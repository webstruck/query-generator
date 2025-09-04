import * as React from "react"
import { Button, type ButtonProps } from "./button"
import { KeyboardShortcut, KEYBOARD_SHORTCUTS, type ShortcutKey } from "./keyboard-shortcut"
import { cn } from "@/lib/utils"

export interface ButtonWithShortcutProps extends ButtonProps {
  shortcut?: ShortcutKey | string[]
  shortcutPlacement?: 'end' | 'start' | 'below'
  showShortcut?: boolean
}

const ButtonWithShortcut = React.forwardRef<HTMLButtonElement, ButtonWithShortcutProps>(
  ({ 
    className, 
    children, 
    shortcut, 
    shortcutPlacement = 'end',
    showShortcut = true,
    ...props 
  }, ref) => {
    const shortcutKeys = React.useMemo(() => {
      if (!shortcut) return undefined
      return typeof shortcut === 'string' ? [...KEYBOARD_SHORTCUTS[shortcut as ShortcutKey]] : [...shortcut]
    }, [shortcut])

    if (!shortcut || !showShortcut || !shortcutKeys) {
      return (
        <Button ref={ref} className={className} {...props}>
          {children}
        </Button>
      )
    }

    if (shortcutPlacement === 'below') {
      return (
        <div className="flex flex-col items-center gap-1">
          <Button ref={ref} className={className} {...props}>
            {children}
          </Button>
          <KeyboardShortcut keys={shortcutKeys} className="text-xs" />
        </div>
      )
    }

    const shortcutElement = <KeyboardShortcut keys={shortcutKeys} />

    return (
      <Button 
        ref={ref} 
        className={cn(
          shortcutPlacement === 'end' ? 'justify-between' : 'justify-start',
          className
        )} 
        {...props}
      >
        {shortcutPlacement === 'start' && shortcutElement}
        <span className={shortcutPlacement === 'end' ? 'flex-1 text-left' : undefined}>
          {children}
        </span>
        {shortcutPlacement === 'end' && shortcutElement}
      </Button>
    )
  }
)
ButtonWithShortcut.displayName = "ButtonWithShortcut"

export { ButtonWithShortcut }