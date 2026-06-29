from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest,
    QAResultRequest, DocsListRequest, WorkflowEngine,
)

SRS_INSPECTION_DIMENSIONS = [
    {"key": "completeness", "label": "完整性", "description": "需求文档是否覆盖了所有必要的功能和非功能需求"},
    {"key": "consistency", "label": "一致性", "description": "文档内容前后是否一致，术语定义是否统一"},
    {"key": "verifiability", "label": "可验证性", "description": "每个需求是否可量化、可测试、可验证"},
    {"key": "unambiguity", "label": "无歧义性", "description": "需求描述是否清晰明确，不存在二义性理解"},
]

@router.post("/{project_id}/step3/artifacts")
def save_step3_artifacts(project_id: str, body: dict = Body(...),
                         db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step3_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤3状态已保存"})


@router.get("/{project_id}/step3/status")
def get_step3_status(project_id: str,
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    artifacts = engine.get_step3_artifacts()
    return APIResponse(code=0, data=artifacts)


@router.post("/{project_id}/step3")
def execute_step3(project_id: str, body: Optional[dict] = None,
                  db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.advance_step(3)
    step = engine.complete_step(3, artifacts=body or {})
    return APIResponse(code=0, data={"message": "第三步：需求分析进行中", "step": step})


@router.post("/{project_id}/step3/qa")
def qa_step3(project_id: str, body: QAResultRequest,
             db: Session = Depends(get_db),
             current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(3)
    else:
        result = engine.fail_qa(3, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"第三步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result})


class Step3ChatRequest(BaseModel):
    message: str
    messages: list = []


@router.post("/{project_id}/step3/chat")
async def step3_chat(project_id: str, body: Step3ChatRequest,
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    """HouXing 需求分析对话 - 使用项目隔离模式"""
    logger.info(f"Step3 chat: project_id={project_id}, message={body.message[:50]}")

    from app.services.gateway_client import GatewayClient
    from app.models.project import Project

    try:
        engine = _get_engine(project_id, db)
        step2 = engine.get_step2_artifacts()
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        # 加载项目信息
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        user_message = body.message or "你好，我们来讨论一下项目的需求。"
        messages = body.messages + [{"role": "user", "content": user_message}]

        # 使用项目隔离模式
        client = GatewayClient(profile_name="houxing", timeout=1200)
        reply_chunks = []
        async for chunk in client.chat_isolated(
            messages=messages,
            project_id=project_id,
            project_name=project.name,
            project_description=project.description or "",
            core_goal=core_goal,
            agent_name="后兴（HouXing）需求分析师",
            stream=False,
        ):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后兴未生成有效回复", data=None)
        return APIResponse(code=0, message="success", data={"reply": reply})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HouXing chat failed: {e}")
        return APIResponse(code=1, message=f"与后兴对话失败，请稍后重试", data=None)


@router.post("/{project_id}/step3/save-doc")
def save_step3_doc(project_id: str, body: Step3InspectRequest,
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    """将需求文档保存到指定文件夹和项目代码库"""
    from datetime import datetime

    # 保存到指定路径
    local_dir = body.save_path or os.path.join(os.getcwd(), "docs")
    os.makedirs(local_dir, exist_ok=True)
    local_filename = body.filename or f"requirements-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    local_path = os.path.join(local_dir, local_filename)
    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(body.content)
        logger.info(f"需求文档已保存到本地: {local_path}")
    except Exception as e:
        logger.error(f"保存需求文档到本地失败: {e}")

    # 同时保存到 WorkflowEngine 产物（供后续步骤读取）
    engine = WorkflowEngine(project_id=project_id, db=db)
    engine.save_step3_artifacts({
        "doc_content": body.content,
        "filename": body.filename or local_filename,
        "local_path": local_path,
        "saved_at": datetime.now().isoformat(),
    })
    engine.complete_step(3)

    # 保存到 Gitea 代码库
    from app.models.repo import Repo
    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        return APIResponse(code=0, data={
            "message": "需求文档已保存到本地和引擎产物",
            "local_path": local_path,
        })

    from app.services.gitea_client import gitea_client
    try:
        owner = settings.GITEA_ADMIN_USER
        filepath = body.filename or f"docs/requirements-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        result = asyncio.run(gitea_client.create_file(
            owner=owner, repo=repo.name,
            filepath=filepath,
            content=body.content,
            message="docs: 提交需求规格说明书（SRS）",
            branch="main",
        ))
        engine.save_step3_artifacts({"filepath": filepath, "commit": result.get("commit", {})})
        return APIResponse(code=0, data={
            "message": "需求文档已保存到本地、代码库和引擎产物",
            "local_path": local_path,
            "filepath": filepath,
            "commit": result.get("commit", {}),
        })
    except Exception as e:
        logger.error(f"保存需求文档到代码库失败: {e}")
        return APIResponse(code=0, data={
            "message": f"需求文档已保存到本地和引擎产物（保存到代码库失败: {e}）",
            "local_path": local_path,
            "filepath": local_filename,
        })


@router.post("/{project_id}/step3/inspect")
async def inspect_step3_srs(project_id: str, body: Step3InspectRequest,
                            db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    """后荣（HouRong）对SRS需求文档进行QA检验（2分钟内完成）"""
    content = body.content
    focus_items = body.focus_items or None
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={
            "passed": False,
            "message": "需求文档内容过短，请补充完善",
            "dimensions": [
                {"key": d["key"], "label": d["label"], "description": d["description"],
                 "passed": False, "detail": "文档内容不足，无法检验"}
                for d in SRS_INSPECTION_DIMENSIONS
            ],
        })

    from app.services.gateway_client import GatewayClient
    import json as _json

    # 确定本次要检验的维度
    active_dims = [d for d in SRS_INSPECTION_DIMENSIONS
                   if not focus_items or d["key"] in focus_items]

    dims_json = _json.dumps(
        [{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims],
        ensure_ascii=False, indent=2
    )

    focus_hint = ""
    if focus_items:
        focus_hint = (
            f"\n⚠️ 本次只需重新检验以下 {len(active_dims)} 项：{[d['label'] for d in active_dims]}\n"
            f"请只针对这些项目做出通过/不通过判定，不要对其他维度提出新的问题。"
        )

    prompt = (
        "你是一个专业的软件需求QA检验员（后荣）。请严格检验以下需求文档是否符合软件需求规格说明书（SRS）标准。\n\n"
        "=== 需求文档 ===\n"
        f"{content}\n\n"
        "=== 检验项目与标准 ===\n"
        f"请依次逐项检验以下 {len(active_dims)} 个维度，对每个维度给出通过/不通过及具体意见：\n"
        f"{dims_json}\n\n"
        "请阅读完整需求文档，严格按照上述检验标准进行专业评审。\n"
        f"{focus_hint}"
        "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。"
        "后续Agent将只根据你的检验报告修改不合格项，禁止扩大修改范围。"
        "已合格维度不得提出修改要求。\n"
        "直接输出 JSON 数组，不要包含其他说明文字：\n"
        "[\n"
        + ",\n".join(
            f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}'
            for d in active_dims
        ) + "\n]"
    )

    INSPECT_TIMEOUT = 120  # 硬限制2分钟
    try:
        client = GatewayClient(profile_name="hourong", timeout=INSPECT_TIMEOUT)

        async def _collect():
            chunks = []
            async for chunk in client.chat_completions(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                max_tokens=2000,
            ):
                chunks.append(chunk)
            return "".join(chunks).strip()

        reply = await asyncio.wait_for(_collect(), timeout=INSPECT_TIMEOUT)

        if not reply:
            raise ValueError("后荣未返回检验结果（空响应）")
        parsed_list = _json.loads(reply)
        if not isinstance(parsed_list, list):
            raise ValueError("返回结果不是数组")
    except asyncio.TimeoutError:
        logger.error(f"后荣检验需求文档超时（{INSPECT_TIMEOUT}s）")
        return APIResponse(code=0, data={
            "passed": False,
            "message": f"检验超时（超过{INSPECT_TIMEOUT//60}分钟），请简化需求文档后重试",
            "dimensions": [
                {"key": d["key"], "label": d["label"], "description": d["description"],
                 "passed": False, "detail": "检验超时，请简化文档后重试"}
                for d in active_dims
            ],
        })
    except Exception as e:
        logger.error(f"后荣检验需求文档失败: {e}")
        logger.error(f"后荣原始回复: {reply if 'reply' in dir() else 'N/A'}")
        return APIResponse(code=0, data={
            "passed": False,
            "message": "后荣检验过程出错，请重试",
            "dimensions": [
                {"key": d["key"], "label": d["label"], "description": d["description"],
                 "passed": False, "detail": f"检验失败: {str(e)[:80]}"}
                for d in active_dims
            ],
        })

    results = []
    for dim in active_dims:
        matched = next((r for r in parsed_list if r.get("key") == dim["key"]), None)
        if matched:
            dim_passed = bool(matched.get("passed", False))
            dim_detail = matched.get("detail", "")
        else:
            dim_passed = False
            dim_detail = "后荣未返回该维度的检验结果"

        results.append({
            "key": dim["key"],
            "label": dim["label"],
            "description": dim["description"],
            "passed": dim_passed,
            "detail": dim_detail,
        })

    all_passed = all(r["passed"] for r in results)

    return APIResponse(code=0, data={
        "passed": all_passed,
        "message": "所有检验项目均通过 ✅" if all_passed else "部分检验项目未通过，请修改后重新检验",
        "dimensions": results,
    })


@router.post("/{project_id}/step3/list-docs")
def list_step3_docs(project_id: str, body: DocsListRequest,
                    current_user=Depends(get_current_user)):
    """从指定文件夹读取文档列表"""
    import glob
    docs_path = body.path
    if not docs_path or not os.path.isdir(docs_path):
        return APIResponse(code=0, data={"files": []})

    files = []
    for f in sorted(glob.glob(os.path.join(docs_path, "*.md"))):
        fname = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            files.append({
                "name": fname,
                "path": f,
                "content": content,
            })
        except Exception as e:
            logger.warning(f"读取文档失败 {f}: {e}")
            files.append({
                "name": fname,
                "path": f,
                "content": "",
            })
    return APIResponse(code=0, data={"files": files})

