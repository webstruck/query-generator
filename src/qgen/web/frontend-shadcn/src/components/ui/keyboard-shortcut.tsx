import React from 'react'
import { cn } from '@/lib/utils'

interface KeyboardShortcutProps {
  keys: string[]
  className?: string
  variant?: 'default' | 'minimal'
}

export const KeyboardShortcut: React.FC<KeyboardShortcutProps> = ({ 
  keys, 
  className = '',
  variant = 'default'
}) => {
  if (variant === 'minimal') {
    return (
      <span className={cn("text-xs text-muted-foreground", className)}>
        {keys.join('+')}
      </span>
    )
  }

  return (
    <span className={cn("inline-flex items-center gap-0.5", className)}>
      {keys.map((key, index) => (
        <React.Fragment key={key}>
          <kbd className="inline-flex h-5 min-w-[20px] items-center justify-center rounded bg-muted/50 px-1.5 text-[10px] font-medium text-muted-foreground ring-1 ring-inset ring-border">
            {key}
          </kbd>
          {index < keys.length - 1 && (
            <span className="text-xs text-muted-foreground mx-0.5">+</span>
          )}
        </React.Fragment>
      ))}
    </span>
  )
}

// Common keyboard shortcuts mapping
export const KEYBOARD_SHORTCUTS = {
  // Primary actions
  approve: ['A'],
  reject: ['R'],
  edit: ['E'],
  save: ['⌘', 'S'],
  delete: ['⌫'],
  
  // Navigation
  next: ['→'],
  previous: ['←'],
  up: ['↑'],
  down: ['↓'],
  
  // Modal/Dialog actions
  submit: ['↵'],
  cancel: ['Esc'],
  close: ['Esc'],
  
  // Selection
  selectAll: ['⌘', 'A'],
  deselectAll: ['⌘', 'D'],
  
  // Common actions
  copy: ['⌘', 'C'],
  paste: ['⌘', 'V'],
  undo: ['⌘', 'Z'],
  redo: ['⌘', '⇧', 'Z'],
  
  // Numbers for quick selection
  option1: ['1'],
  option2: ['2'],
  option3: ['3'],
  option4: ['4'],
  option5: ['5'],
  
  // Special actions
  skip: ['S'],
  discard: ['⌘', '⌫'],
  export: ['⌘', 'E'],
  refresh: ['⌘', 'R'],
  
  // View actions
  fullscreen: ['F'],
  zoom: ['⌘', '+'],
  zoomOut: ['⌘', '-'],
  
  // Help
  help: ['?']
} as const

export type ShortcutKey = keyof typeof KEYBOARD_SHORTCUTS