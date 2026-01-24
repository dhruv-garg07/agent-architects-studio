# File System Design System (Agent Dashboard)

## Overview
The file system component in `agent_dashboard.html` uses a glassmorphic, high-contrast dark mode design with color-coded semantic sections.

## Container Styling
- **Background**: `bg-[rgba(255,255,255,0.02)]` (Subtle glass)
- **Effect**: `backdrop-blur-xl`
- **Border**: `border border-[rgba(255,255,255,0.1)]`
- **Rounded**: `rounded-2xl`
- **Shadow**: `shadow-xl`

## Header Section
- **Title**: `FileSystem` (White, Semibold)
- **Icon**: `folder-tree` (Text-Primary)
- **Badge**: `bg-[rgba(255,255,255,0.1)] text-gray-400` (e.g., "3 Sources")

## Section Categories (Folder Groups)

### 1. Context Store (Memorization)
- **Color Theme**: Primary Blue (Default)
- **Icon**: `folder-open`
- **Icon Container**: `bg-primary/20 text-primary`
- **Subtitle**: "Memory Bins"

### 2. Documents (Knowledge)
- **Color Theme**: Primary Blue
- **Icon**: `file-text`
- **Icon Container**: `bg-primary/20 text-primary`
- **Subtitle**: "Knowledge Base"

### 3. Checkpoints (State)
- **Color Theme**: Emerald Green (`#10b981`)
- **Icon**: `save`
- **Icon Container**: `bg-[rgba(16,185,129,0.2)] text-[#34d399]`
- **Subtitle**: "State History"

### 4. Activity Logs (System)
- **Color Theme**: Amber/Warning (`#f59e0b`)
- **Icon**: `scroll-text`
- **Icon Container**: `bg-[rgba(245,158,11,0.2)] text-[#fbbf24]`
- **Subtitle**: "System Events"

## Navigation Items (Sub-folders)
- **Indentation**: `pl-14` (Aligned with text content of parent)
- **Text**: `text-gray-400` -> `hover:text-gray-200`
- **Icon**: `folder` (Gray -> Colored on hover)
- **Count Badge**: `text-xs text-gray-600` on right
