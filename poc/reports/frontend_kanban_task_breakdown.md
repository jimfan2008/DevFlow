# DevFlow 看板模块技术选型报告与实现方案

## 一、概述

本报告针对 DevFlow 项目看板模块进行技术选型和任务拆分，提供完整的前端实现方案。

---

## 二、UI 组件库选型分析

### 2.1 候选方案对比

| 特性 | Ant Design | Material-UI (MUI) |
|------|-----------|-------------------|
| **成熟度** | ⭐⭐⭐⭐⭐ 业界领先 | ⭐⭐⭐⭐⭐ 成熟稳定 |
| **React 版本** | React 16+ | React 16+ (v5+ 支持 React 18) |
| **TypeScript 支持** | ⭐⭐⭐⭐⭐ 优秀 | ⭐⭐⭐⭐⭐ 优秀 |
| **组件丰富度** | ⭐⭐⭐⭐⭐ 70+ 组件 | ⭐⭐⭐⭐⭐ 50+ 组件 |
| **文档质量** | ⭐⭐⭐⭐⭐ 中文友好 | ⭐⭐⭐⭐ 英文为主 |
| **定制化** | ⭐⭐⭐⭐ 主题系统 | ⭐⭐⭐⭐⭐ Material Design |
| **性能** | ⭐⭐⭐⭐ 按需加载 | ⭐⭐⭐⭐⭐ 树摇优化 |
| **社区活跃度** | ⭐⭐⭐⭐⭐ 阿里维护 | ⭐⭐⭐⭐⭐ Google 社区 |
| **学习曲线** | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 较低 |

### 2.2 推荐方案

**推荐：Ant Design**

**理由：**
1. **中文文档完善** - 更适合国内开发团队
2. **企业级组件** - 表单、表格、布局等专业组件丰富
3. **主题定制灵活** - 支持 CSS Variables 主题切换
4. **生态完善** - 与 Ant Design Pro 集成度高
5. **性能优化** - 支持组件按需加载和 Tree Shaking

### 2.3 替代方案

**Material-UI** - 如果团队偏好 Material Design 设计风格

---

## 三、拖拽库选型分析

### 3.1 候选方案对比

| 特性 | react-beautiful-dnd | dnd-kit |
|------|--------------------|---------|
| **维护状态** | ⚠️ 维护放缓 | ⭐⭐⭐⭐⭐ 活跃开发 |
| **React 18 支持** | ⚠️ 部分支持 | ⭐⭐⭐⭐⭐ 完全支持 |
| **TypeScript** | ⭐⭐⭐⭐ 类型定义完整 | ⭐⭐⭐⭐⭐ 原生支持 |
| **可访问性** | ⭐⭐⭐ 基础支持 | ⭐⭐⭐⭐⭐ 优秀 |
| **性能** | ⭐⭐⭐⭐ 良好 | ⭐⭐⭐⭐⭐ 虚拟化支持 |
| **灵活性** | ⭐⭐⭐ 固定模式 | ⭐⭐⭐⭐⭐ 高度可定制 |
| **学习曲线** | ⭐⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 较陡 |
| **Bundle 大小** | 75KB GZipped | 15KB GZipped |

### 3.2 推荐方案

**推荐：dnd-kit**

**理由：**
1. **现代架构** - 模块化设计，更灵活
2. **轻量级** - Bundle 小 5 倍
3. **性能优化** - 支持虚拟化和性能监控
4. **可访问性** - WCAG 2.1 合规
5. **活跃维护** - 持续更新，React 18 友好

### 3.3 备选方案

**react-beautiful-dnd** - 如果团队熟悉 API，迁移成本低

---

## 四、技术选型总结

| 类别 | 推荐方案 | 备选方案 | 理由 |
|------|---------|---------|------|
| UI 组件库 | **Ant Design 5** | Material-UI | 中文文档、企业级组件 |
| 拖拽库 | **dnd-kit** | react-beautiful-dnd | 轻量、活跃、可访问性 |
| 状态管理 | **Zustand** | Redux Toolkit | 简洁、TypeScript 友好 |
| 数据请求 | **TanStack Query** | Axios | 缓存、重试、优化 |
| 表单处理 | **React Hook Form** | Formik | 性能、TypeScript |

---

## 五、任务拆分清单

### 5.1 环境搭建 (预计 0.5 人天)

- [ ] 创建 React + TypeScript 项目 (Vite)
- [ ] 安装依赖: Ant Design, dnd-kit, Zustand, TanStack Query
- [ ] 配置 ESLint + Prettier
- [ ] 配置 TypeScript 路径别名
- [ ] 创建基础目录结构

### 5.2 基础组件开发 (预计 2 人天)

#### 5.2.1 看板容器组件
- [ ] KanbanBoard - 主容器
- [ ] KanbanColumn - 看板列
- [ ] KanbanCard - 看板卡片
- [ ] KanbanHeader - 看板头部

#### 5.2.2 卡片组件
- [ ] CardTitle - 卡片标题
- [ ] CardDescription - 卡片描述
- [ ] CardTags - 卡片标签
- [ ] CardAssignees - 卡片负责人
- [ ] CardDueDate - 截止日期
- [ ] CardAttachments - 附件列表

#### 5.2.3 交互组件
- [ ] AddCardModal - 添加卡片模态框
- [ ] CardDetailModal - 卡片详情模态框
- [ ] DragHandle - 拖拽手柄
- [ ] ColumnHeader - 列头部（含列操作）

### 5.3 状态管理 (预计 1 人天)

#### 5.3.1 Zustand Store
```typescript
// store/kanbanStore.ts
interface KanbanState {
  // 数据
  columns: Column[]
  cards: Card[]
  
  // 操作
  addColumn: (column: Partial<Column>) => void
  updateColumn: (id: string, data: Partial<Column>) => void
  deleteColumn: (id: string) => void
  addCard: (card: Partial<Card>, columnId: string) => void
  updateCard: (id: string, data: Partial<Card>) => void
  deleteCard: (id: string) => void
  moveCard: (cardId: string, fromColumnId: string, toColumnId: string, newIndex: number) => void
  
  // UI 状态
  selectedCard: Card | null
  showModal: boolean
  modalType: 'addCard' | 'editCard' | 'viewCard'
  
  // 操作
  openModal: (type: 'addCard' | 'editCard' | 'viewCard', card?: Card) => void
  closeModal: () => void
}
```

#### 5.3.2 状态持久化
- [ ] localStorage 同步
- [ ] 状态变更日志

### 5.4 API 集成 (预计 1.5 人天)

#### 5.4.1 API 服务层
```typescript
// services/kanbanApi.ts
interface KanbanApi {
  // 列管理
  getColumns: () => Promise<Column[]>
  createColumn: (data: CreateColumnDto) => Promise<Column>
  updateColumn: (id: string, data: UpdateColumnDto) => Promise<Column>
  deleteColumn: (id: string) => Promise<void>
  
  // 卡片管理
  getCards: (columnId?: string) => Promise<Card[]>
  createCard: (data: CreateCardDto) => Promise<Card>
  updateCard: (id: string, data: UpdateCardDto) => Promise<Card>
  deleteCard: (id: string) => Promise<void>
  moveCard: (data: MoveCardDto) => Promise<Card>
  
  // 批量操作
  bulkUpdateCards: (cards: UpdateCardDto[]) => Promise<Card[]>
}
```

#### 5.4.2 TanStack Query 集成
- [ ] QueryClient 配置
- [ ] 自定义 Hook: useColumns, useCards, useCard
- [ ] 查询优化: 分页、缓存策略
- [ ] 乐观更新配置

### 5.5 拖拽功能实现 (预计 1.5 人天)

#### 5.5.1 dnd-kit 配置
```typescript
// components/KanbanBoard.tsx
import {
  DndContext,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
  DragStart,
  DragOver,
  DragEnd,
} from '@dnd-kit/core'
import {
  sortableKeyboardCoordinates,
  KeyboardSensor,
} from '@dnd-kit/modifiers/keyboard'
import {
  restrictToParentElement,
  restrictToVerticalAxis,
} from '@dnd-kit/modifiers'
```

#### 5.5.2 拖拽事件处理
- [ ] DragStart: 记录起始位置
- [ ] DragOver: 计算目标位置
- [ ] DragEnd: 提交移动操作
- [ ] 键盘支持 (Tab, Enter, Space)

#### 5.5.3 视觉反馈
- [ ] 拖拽卡片的半透明效果
- [ ] 目标位置的占位符
- [ ] 列切换动画

### 5.6 响应式设计 (预计 0.5 人天)

- [ ] 桌面端 (≥1024px) - 完整功能
- [ ] 平板端 (768-1023px) - 水平滚动
- [ ] 移动端 (<768px) - 垂直堆叠

### 5.7 性能优化 (预计 1 人天)

#### 5.7.1 渲染优化
- [ ] React.memo 应用
- [ ] useMemo/useCallback 缓存
- [ ] 虚拟列表 (卡片过多时)

#### 5.7.2 加载优化
- [ ] 图片懒加载
- [ ] 骨架屏
- [ ] 分块加载

### 5.8 测试 (预计 1 人天)

#### 5.8.1 单元测试
- [ ] Jest + React Testing Library
- [ ] 组件测试覆盖率 > 80%
- [ ] 状态管理测试
- [ ] API 集成测试

#### 5.8.2 E2E 测试
- [ ] Cypress/Playwright
- [ ] 拖拽功能测试
- [ ] 关键流程测试

### 5.9 文档 (预计 0.5 人天)

- [ ] 组件使用文档
- [ ] API 接口文档
- [ ] 开发规范文档
- [ ] 部署指南

---

## 六、实现方案详情

### 6.1 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── KanbanBoard/
│   │   │   ├── index.tsx
│   │   │   ├── KanbanBoard.tsx
│   │   │   ├── KanbanColumn.tsx
│   │   │   ├── KanbanCard.tsx
│   │   │   └── styles.ts
│   │   ├── Card/
│   │   │   ├── CardTitle.tsx
│   │   │   ├── CardDescription.tsx
│   │   │   ├── CardTags.tsx
│   │   │   ├── CardAssignees.tsx
│   │   │   ├── CardDueDate.tsx
│   │   │   └── AddCardButton.tsx
│   │   ├── Modal/
│   │   │   ├── CardDetailModal.tsx
│   │   │   └── AddCardModal.tsx
│   │   └── shared/
│   │       ├── DragHandle.tsx
│   │       └── Loading.tsx
│   ├── hooks/
│   │   ├── useKanban.ts
│   │   ├── useDragDrop.ts
│   │   └── useCardActions.ts
│   ├── store/
│   │   ├── kanbanStore.ts
│   │   └── selectors.ts
│   ├── services/
│   │   ├── kanbanApi.ts
│   │   └── apiClient.ts
│   ├── queries/
│   │   ├── useColumns.ts
│   │   ├── useCards.ts
│   │   └── useCard.ts
│   ├── types/
│   │   ├── kanban.ts
│   │   └── api.ts
│   ├── utils/
│   │   ├── dragUtils.ts
│   │   └── validators.ts
│   └── styles/
│       ├── variables.css
│       └── global.css
├── public/
├── tests/
│   ├── components/
│   ├── hooks/
│   └── e2e/
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 6.2 核心代码示例

#### 状态管理 (Zustand)
```typescript
// store/kanbanStore.ts
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

interface Column {
  id: string
  title: string
  order: number
  color?: string
}

interface Card {
  id: string
  columnId: string
  title: string
  description?: string
  tags?: string[]
  assignees?: string[]
  dueDate?: string
  order: number
}

interface KanbanState {
  columns: Column[]
  cards: Card[]
  selectedCard: Card | null
  modalOpen: boolean
  modalType: 'add' | 'edit' | 'view'
  
  // 列操作
  addColumn: (column: Omit<Column, 'id'>) => void
  updateColumn: (id: string, updates: Partial<Column>) => void
  deleteColumn: (id: string) => void
  
  // 卡片操作
  addCard: (card: Omit<Card, 'id'>) => void
  updateCard: (id: string, updates: Partial<Card>) => void
  deleteCard: (id: string) => void
  moveCard: (cardId: string, newColumnId: string, newIndex: number) => void
  
  // UI 操作
  setSelectedCard: (card: Card | null) => void
  openModal: (type: 'add' | 'edit' | 'view', card?: Card) => void
  closeModal: () => void
}

export const useKanbanStore = create<KanbanState>()(
  devtools(
    persist(
      immer((set, get) => ({
        columns: [],
        cards: [],
        selectedCard: null,
        modalOpen: false,
        modalType: 'add',
        
        addColumn: (column) => set((state) => {
          state.columns.push({ ...column, id: crypto.randomUUID() })
        }),
        
        updateColumn: (id, updates) => set((state) => {
          const column = state.columns.find(c => c.id === id)
          if (column) Object.assign(column, updates)
        }),
        
        deleteColumn: (id) => set((state) => {
          state.columns = state.columns.filter(c => c.id !== id)
        }),
        
        addCard: (card) => set((state) => {
          state.cards.push({ ...card, id: crypto.randomUUID() })
        }),
        
        updateCard: (id, updates) => set((state) => {
          const card = state.cards.find(c => c.id === id)
          if (card) Object.assign(card, updates)
        }),
        
        deleteCard: (id) => set((state) => {
          state.cards = state.cards.filter(c => c.id !== id)
        }),
        
        moveCard: (cardId, newColumnId, newIndex) => set((state) => {
          const card = state.cards.find(c => c.id === cardId)
          if (card) {
            card.columnId = newColumnId
            card.order = newIndex
          }
        }),
        
        setSelectedCard: (card) => set({ selectedCard: card }),
        
        openModal: (type, card) => set({ modalOpen: true, modalType: type, selectedCard: card || null }),
        
        closeModal: () => set({ modalOpen: false, selectedCard: null })
      })),
      { name: 'kanban-storage' }
    )
  )
)
```

#### 拖拽功能 (dnd-kit)
```typescript
// components/KanbanBoard/DragDropContext.tsx
import {
  DndContext,
  DragStart,
  DragOver,
  DragEnd,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
  KeyboardSensor,
} from '@dnd-kit/core'
import {
  restrictToVerticalAxis,
  restrictToParentElement,
} from '@dnd-kit/modifiers'
import { useState, useMemo } from 'react'
import { useKanbanStore } from '../../store/kanbanStore'

interface DragItem {
  type: 'card' | 'column'
  id: string
}

export const DragDropContext: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { moveCard, updateColumnOrder } = useKanbanStore()
  const [activeId, setActiveId] = useState<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)

  const sensors = useMemo(() => [
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 拖动 8px 后激活
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  ], [])

  const handleDragStart = (event: DragStart) => {
    setActiveId(event.active.id as string)
  }

  const handleDragOver = (event: DragOver) => {
    setOverId(event.over?.id as string)
  }

  const handleDragEnd = (event: DragEnd) => {
    const { active, over } = event
    
    if (over && active.id !== over.id) {
      // 处理卡片移动
      if (active.id.toString().includes('card-')) {
        moveCard(
          active.id.toString().replace('card-', ''),
          over.id.toString().replace('column-', ''),
          0
        )
      }
    }
    
    setActiveId(null)
    setOverId(null)
  }

  return (
    <DndContext
      sensors={sensors}
      modifiers={[restrictToVerticalAxis, restrictToParentElement]}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      {children}
      <DragOverlay>
        {activeId ? (
          <CardOverlay cardId={activeId.replace('card-', '')} />
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
```

---

## 七、开发计划

| 阶段 | 内容 | 工时 | 产出 |
|------|------|------|------|
| **Phase 1** | 环境搭建 + 基础组件 | 2.5 天 | 可渲染的基础看板 |
| **Phase 2** | 状态管理 + API 集成 | 2.5 天 | 完整 CRUD 功能 |
| **Phase 3** | 拖拽功能 | 1.5 天 | 可拖拽的看板 |
| **Phase 4** | 优化 + 测试 | 2.5 天 | 生产就绪 |

**总工时：9 人天**

---

## 八、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| dnd-kit 学习曲线 | 开发延迟 | 预留学习时间，参考示例 |
| 性能问题（大量数据） | 用户体验 | 虚拟列表、分块渲染 |
| API 变更 | 集成失败 | 抽象服务层、接口契约 |
| 浏览器兼容 | 功能异常 | 渐进增强、兼容性测试 |

---

## 九、依赖安装

```bash
# 核心依赖
npm install antd @ant-design/icons dnd-kit/core @dnd-kit/modifiers

# 状态管理
npm install zustand

# 数据请求
npm install @tanstack/react-query axios

# 表单处理
npm install react-hook-form @hookform/resolvers

# 开发工具
npm install -D @types/node vite vite-plugin-pwa

# 测试
npm install -D @testing-library/react @testing-library/jest-dom jest
```

---

## 十、参考资源

- [Ant Design 官方文档](https://ant.design/docs/react/introduce-cn)
- [dnd-kit 官方文档](https://docs.dndkit.com/)
- [Zustand 官方文档](https://zustand-demo.pmnd.rs/)
- [TanStack Query 官方文档](https://tanstack.com/query/latest)

---

**报告版本**: 1.0.0  
**创建日期**: 2026-05-11  
**作者**: DevFlow 团队
