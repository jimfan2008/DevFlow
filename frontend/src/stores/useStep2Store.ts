import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { workflowApi, chatApi } from '@/api'
import type { ChatGroup } from '@/types/api'

export interface AgentRole {
  name: string
  chineseName: string
  role: string
  responsibility: string
  activated: boolean
}

export interface ChatMessage {
  role: 'haimei' | 'user' | 'system'
  content: string
}

export type Step2Phase =
  | 'intro'
  | 'chatting'
  | 'confirming'
  | 'organizing'
  | 'grouping'
  | 'qa'
  | 'complete'

export const AGENT_ROLES: AgentRole[] = [
  { name: 'HaiMei', chineseName: '海梅', role: '项目经理（默认Hermes Agent）', responsibility: '负责任务分派，对项目的交付成果负责', activated: false },
  { name: 'HouXing', chineseName: '后兴', role: '需求分析师', responsibility: '负责需求分析，产出完整、准确的软件需求说明书', activated: false },
  { name: 'HouWang', chineseName: '后旺', role: '架构设计师', responsibility: '负责架构设计、后端设计、前端设计、数据库设计等', activated: false },
  { name: 'HouFa', chineseName: '后发', role: '程序员', responsibility: '负责建立代码编写Agent蜂群，监督蜂群完成TDD测试用例和代码编写', activated: false },
  { name: 'HouDa', chineseName: '后达', role: '测试员', responsibility: '负责建立代码测试Agent蜂群，执行单元测试、模块测试、集成测试、前端实操验证', activated: false },
  { name: 'HouFu', chineseName: '后富', role: 'CI/CD工程师', responsibility: '专门负责开发环境搭建和代码部署到测试环境或生产环境', activated: false },
  { name: 'HouGui', chineseName: '后贵', role: '文档管理员', responsibility: '负责整个项目的文档一致性管理', activated: false },
  { name: 'HouRong', chineseName: '后荣', role: 'QA', responsibility: '负责检验每个Agent的产出是否达到验收标准，未达标退回重做，达标放行并提交代码库', activated: false },
  { name: 'HouHua', chineseName: '后华', role: '安全员', responsibility: '负责代码审计、合规审查、渗透测试、漏洞修复等', activated: false },
]

export const useStep2Store = defineStore('step2', () => {
  const phase = ref<Step2Phase>('intro')
  const messages = ref<ChatMessage[]>([])
  const chatRound = ref(0)
  const coreGoal = ref('')
  const confirmedGoal = ref('')
  const agents = ref<AgentRole[]>(AGENT_ROLES.map(a => ({ ...a })))
  const groupInfo = ref<ChatGroup | null>(null)
  const qaPassed = ref(false)
  const qaMessage = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const projectId = ref('')
  const projectName = ref('')
  const _restored = ref(false)

  const currentAgentStatus = computed(() => {
    const total = agents.value.length
    const activated = agents.value.filter(a => a.activated).length
    return `${activated} / ${total}`
  })

  function toSaveData() {
    return {
      phase: phase.value,
      core_goal: coreGoal.value,
      confirmed_goal: confirmedGoal.value,
      chat_round: chatRound.value,
      messages: messages.value.map(m => ({ role: m.role, content: m.content })),
      agents: agents.value.map(a => ({ ...a })),
      group_info: groupInfo.value,
      qa_passed: qaPassed.value,
      qa_message: qaMessage.value,
    }
  }

  async function saveToBackend() {
    if (!projectId.value) return
    _restored.value = true
    try {
      await workflowApi.saveStep2Artifacts(projectId.value, toSaveData())
    } catch {
      // 静默保存失败
    }
  }

  async function loadFromBackend(pid: string): Promise<boolean> {
    try {
      const res = await workflowApi.getStep2Status(pid) as any
      const data = res?.data || res
      if (!data || !data.phase) return false

      phase.value = data.phase
      coreGoal.value = data.core_goal || ''
      confirmedGoal.value = data.confirmed_goal || ''
      chatRound.value = data.chat_round || 0
      messages.value = (data.messages || []).map((m: any) => ({ role: m.role, content: m.content }))
      if (data.agents) {
        agents.value = AGENT_ROLES.map(a => {
          const saved = (data.agents as any[]).find((sa: any) => sa.name === a.name)
          return saved || { ...a }
        })
      }
      groupInfo.value = data.group_info || null
      qaPassed.value = data.qa_passed || false
      qaMessage.value = data.qa_message || ''
      _restored.value = true
      return true
    } catch {
      return false
    }
  }

  function reset(pid: string, pname: string) {
    phase.value = 'intro'
    messages.value = []
    chatRound.value = 0
    coreGoal.value = ''
    confirmedGoal.value = ''
    agents.value = AGENT_ROLES.map(a => ({ ...a }))
    groupInfo.value = null
    qaPassed.value = false
    qaMessage.value = ''
    loading.value = false
    error.value = null
    projectId.value = pid
    projectName.value = pname
    _restored.value = false
  }

  function addMessage(role: ChatMessage['role'], content: string) {
    messages.value.push({ role, content })
  }

  function startConversation() {
    if (_restored.value) return
    const intro = `你好！我是**海梅（HaiMei）**，你的专属项目经理 🤝

我将全程负责你的项目交付，确保每一步都高质量完成。

首先，让我确认一下项目的**核心目标**。请描述你想要开发的项目——它的主要功能、目标用户，以及你希望通过它解决什么问题。`
    addMessage('haimei', intro)
  }

  function simulateHaimeiResponse(userInput: string) {
    const round = chatRound.value
    chatRound.value++

    let response = ''

    if (round === 0) {
      coreGoal.value = userInput.replace(/^(我想|我要|我希望|打算|计划)\s*/i, '').trim()
      const hasDetail = /[。，;；]/.test(userInput) && userInput.length > 15
      if (hasDetail) {
        response = `感谢你的详细描述！我已经对项目有了初步了解。

我来梳理一下关键点：
- **项目方向**: ${userInput.slice(0, 60)}${userInput.length > 60 ? '...' : ''}

能否告诉我更多关于以下方面的信息？
1. 项目的**主要功能模块**有哪些？
2. **目标用户群体**是谁？
3. 是否有**时间或预算要求**？`
      } else {
        response = `感谢你的分享！为了更好地理解你的需求，我想了解更多细节：

1. 这个项目的**核心功能**是什么？
2. **目标用户**是谁？
3. 你有什么**特别的期望或要求**吗？

请详细描述一下，这样我可以帮你提炼出清晰的项目核心目标。`
      }
    } else if (round === 1) {
      const goalText = userInput.length > 20 ? userInput.slice(0, 100) : userInput
      coreGoal.value = goalText
      response = `非常好！我现在对项目有了更清晰的认识。

基于我们的讨论，我将项目的**核心目标**初步概括为：

> **${goalText}${userInput.length > 100 ? '...' : ''}**

请确认这个核心目标是否准确？如果需要调整，请告诉我你的想法。
- 如果**确认无误**，请回复"确认"或"没问题"
- 如果**需要修改**，请补充你的修改意见`
    } else if (round >= 2) {
      const confirmWords = ['确认', '没问题', '可以', '同意', '是的', '对的', '正确', '好的', 'ok', 'yes', '对', '行']
      const isConfirmed = confirmWords.some(w => userInput.toLowerCase().includes(w.toLowerCase()))
      if (isConfirmed) {
        confirmedGoal.value = coreGoal.value
        response = `太好了！项目核心目标已确认 ✅

> **${confirmedGoal.value}**

接下来，我将为你搭建项目的**组织架构**，激活9个专业Agent角色，为项目的顺利推进做好准备！`
        setTimeout(() => { phase.value = 'organizing'; saveToBackend() }, 500)
      } else {
        coreGoal.value = userInput.replace(/^(修改|调整|改为|改成|更新)\s*/i, '').trim() || userInput
        response = `已收到你的修改意见！我更新了核心目标为：

> **${coreGoal.value}**

如果确认无误，请回复"确认"或"没问题"来锁定核心目标。`
      }
    }

    setTimeout(() => {
      addMessage('haimei', response)
    }, 600)
  }

  async function sendMessage(text: string) {
    if (!text.trim() || loading.value) return
    loading.value = true
    addMessage('user', text.trim())

    if (phase.value === 'intro' || phase.value === 'chatting') {
      phase.value = 'chatting'
      simulateHaimeiResponse(text.trim())
    } else if (phase.value === 'confirming') {
      const confirmWords = ['确认', '没问题', '可以', '同意', '是的', '对的', '正确', '好的', 'ok', 'yes', '对', '行']
      const isConfirmed = confirmWords.some(w => text.toLowerCase().includes(w.toLowerCase()))
      if (isConfirmed) {
        confirmedGoal.value = coreGoal.value
        addMessage('haimei', `太好了！项目核心目标已确认 ✅\n\n> **${confirmedGoal.value}**\n\n接下来，我将为你搭建项目的**组织架构**，激活9个专业Agent角色！`)
        setTimeout(() => { phase.value = 'organizing'; saveToBackend() }, 800)
      } else {
        coreGoal.value = text.trim()
        addMessage('haimei', `已更新核心目标为：\n\n> **${coreGoal.value}**\n\n请确认是否准确？回复"确认"来锁定。`)
      }
    }

    await new Promise(r => setTimeout(r, 100))
    loading.value = false
  }

  async function activateAgents() {
    phase.value = 'organizing'
    for (let i = 0; i < agents.value.length; i++) {
      await new Promise(r => setTimeout(r, 300))
      agents.value[i].activated = true
    }
    addMessage('system', '✅ 所有Agent角色已成功激活！项目组织架构搭建完成。')
    addMessage('haimei', '组织架构已搭建完成！所有9个Agent角色已各就各位。现在让我创建**项目讨论群**，将所有成员加入群组。')
    await new Promise(r => setTimeout(r, 500))
    phase.value = 'grouping'
    await saveToBackend()
    await createDiscussionGroup()
  }

  async function createDiscussionGroup() {
    loading.value = true
    error.value = null
    try {
      const agentNames = agents.value.map(a => a.name)
      const res = await chatApi.createGroup({
        name: `${projectName.value} - 项目团队`,
        members: agentNames,
        project_id: projectId.value,
      }) as any
      const groupData = res?.data?.group || res?.data
      if (groupData) {
        groupInfo.value = groupData as ChatGroup
        addMessage('system', `✅ 讨论群「${groupData.name}」已创建，所有Agent已加入群组。`)
        addMessage('haimei', '项目讨论群已建立！所有成员已就位 🎉\n\n群组支持**讨论模式**（自由发言）和**会议模式**（结构化议程）。\n\n现在让**后荣**（QA）进行最终检验。')

        const allMembersPresent = groupData.members?.length >= 9
        if (!allMembersPresent) {
          addMessage('system', '⚠️ 注意：部分Agent成员尚未加入群组，请检查成员列表。')
        }

        await new Promise(r => setTimeout(r, 500))
        phase.value = 'qa'
        await saveToBackend()
        await runQACheck()
      } else {
        throw new Error('创建群组失败：未返回群组数据')
      }
    } catch (e: any) {
      error.value = e.message || '创建讨论群失败'
      ElMessage.error(error.value)
      addMessage('system', `❌ 创建讨论群失败：${error.value}`)
      phase.value = 'grouping'
    } finally {
      loading.value = false
    }
  }

  async function runQACheck() {
    loading.value = true
    error.value = null

    const checks: { name: string; passed: boolean; detail: string }[] = []

    checks.push({
      name: '核心目标明确性',
      passed: confirmedGoal.value.length >= 5,
      detail: confirmedGoal.value.length >= 5
        ? `核心目标已确认：${confirmedGoal.value}`
        : '核心目标未明确或长度不足',
    })

    const allActivated = agents.value.every(a => a.activated)
    checks.push({
      name: '组织架构完整性',
      passed: allActivated,
      detail: allActivated
        ? `所有9个Agent角色已激活（${agents.value.map(a => a.chineseName).join('、')}）`
        : '部分Agent角色未激活',
    })

    const groupExists = groupInfo.value !== null
    const memberCount = groupInfo.value?.members?.length || 0
    checks.push({
      name: '讨论群组状态',
      passed: groupExists && memberCount >= 9,
      detail: groupExists
        ? `讨论群「${groupInfo.value!.name}」已建立，成员 ${memberCount}/9 人`
        : '讨论群未创建',
    })

    await new Promise(r => setTimeout(r, 800))

    const allPassed = checks.every(c => c.passed)
    qaPassed.value = allPassed
    qaMessage.value = allPassed
      ? '所有检验项均通过 ✅'
      : `以下检验项未通过：${checks.filter(c => !c.passed).map(c => c.name).join('、')}`

    if (allPassed) {
      addMessage('system', `✅ **后荣（QA）检验通过**`)
      checks.forEach(c => {
        addMessage('system', `  ✓ ${c.name}：${c.detail}`)
      })
      addMessage('haimei', '🎉 **QA检验全部通过！** 第二步已圆满完成。\n\n核心目标已确认、组织架构已搭建、讨论群已建立。让我们进入下一步！')
      await new Promise(r => setTimeout(r, 500))
      phase.value = 'complete'
      await saveToBackend()
    } else {
      addMessage('system', `❌ **QA检验未通过**`)
      checks.filter(c => !c.passed).forEach(c => {
        addMessage('system', `  ✗ ${c.name}：${c.detail}`)
      })
      qaPassed.value = false
    }

    loading.value = false
  }

  async function completeStep() {
    loading.value = true
    error.value = null
    try {
      const res = await workflowApi.executeStep2(projectId.value, confirmedGoal.value) as any
      ElMessage.success('第二步完成：核心目标确认与组织架构搭建')
      return res?.data || res
    } catch (e: any) {
      error.value = e.message || '完成步骤失败'
      ElMessage.error(error.value)
      return null
    } finally {
      loading.value = false
    }
  }

  async function executeStep3() {
    try {
      await workflowApi.executeStep3(projectId.value, {
        core_goal: confirmedGoal.value,
        confirmed_goal: confirmedGoal.value,
        group_info: groupInfo.value,
        agents: agents.value.map(a => ({ ...a })),
      })
    } catch (e: any) {
      console.error('进入第三步失败:', e)
    }
  }

  function confirmGoalDirectly(goal: string) {
    confirmedGoal.value = goal
    coreGoal.value = goal
    addMessage('system', `✅ 核心目标已确认：${goal}`)
    addMessage('haimei', '核心目标已确认！接下来搭建项目组织架构...')
    setTimeout(() => { phase.value = 'organizing'; saveToBackend() }, 500)
  }

  return {
    phase, messages, chatRound, coreGoal, confirmedGoal,
    agents, groupInfo, qaPassed, qaMessage, loading, error,
    projectId, projectName, currentAgentStatus,
    _restored,
    reset, addMessage, startConversation, sendMessage,
    activateAgents, createDiscussionGroup, runQACheck,
    completeStep, executeStep3, confirmGoalDirectly,
    loadFromBackend, saveToBackend,
  }
})
