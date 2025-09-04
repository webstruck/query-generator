import { useEffect, useCallback } from 'react'

export interface ShortcutHandler {
  keys: string[]
  handler: (event: KeyboardEvent) => void
  description?: string
  enabled?: boolean
  preventDefault?: boolean
}

export interface UseKeyboardShortcutsOptions {
  shortcuts: ShortcutHandler[]
  enabled?: boolean
  ignoreWhenFocused?: string[] // CSS selectors or tag names to ignore when focused
}

export const useKeyboardShortcuts = ({ 
  shortcuts, 
  enabled = true,
  ignoreWhenFocused = ['input', 'textarea', '[contenteditable="true"]']
}: UseKeyboardShortcutsOptions) => {
  
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return

    // Check if we should ignore this event based on focused element
    const activeElement = document.activeElement
    if (activeElement) {
      const shouldIgnore = ignoreWhenFocused.some(selector => {
        if (selector.toLowerCase() === activeElement.tagName.toLowerCase()) {
          return true
        }
        if (selector.startsWith('[') && selector.endsWith(']')) {
          const attr = selector.slice(1, -1).split('=')[0]
          return activeElement.hasAttribute(attr)
        }
        try {
          return activeElement.matches(selector)
        } catch {
          return false
        }
      })
      if (shouldIgnore) return
    }

    // Check each shortcut
    for (const shortcut of shortcuts) {
      if (!shortcut.enabled && shortcut.enabled !== undefined) continue

      const matches = checkKeysMatch(event, shortcut.keys)
      if (matches) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault()
        }
        shortcut.handler(event)
        break // Only handle the first matching shortcut
      }
    }
  }, [shortcuts, enabled, ignoreWhenFocused])

  useEffect(() => {
    if (!enabled) return

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown, enabled])
}

// Helper function to check if the pressed keys match the shortcut
const checkKeysMatch = (event: KeyboardEvent, targetKeys: string[]): boolean => {
  const pressedKeys: string[] = []
  
  // Add modifier keys
  if (event.metaKey || event.ctrlKey) pressedKeys.push('⌘')
  if (event.altKey) pressedKeys.push('⌥')
  if (event.shiftKey) pressedKeys.push('⇧')
  
  // Add the main key
  const key = event.key
  
  // Map common keys to symbols
  const keyMappings: Record<string, string> = {
    'Enter': '↵',
    'Escape': 'Esc',
    'ArrowLeft': '←',
    'ArrowRight': '→',
    'ArrowUp': '↑',
    'ArrowDown': '↓',
    'Backspace': '⌫',
    'Delete': '⌦',
    'Tab': '⇥',
    'Space': '⎵',
    ' ': '⎵'
  }
  
  const mappedKey = keyMappings[key] || key.toUpperCase()
  pressedKeys.push(mappedKey)
  
  // Check if pressed keys match target keys
  if (pressedKeys.length !== targetKeys.length) return false
  
  return targetKeys.every(targetKey => 
    pressedKeys.includes(targetKey) || 
    pressedKeys.includes(targetKey.toUpperCase())
  )
}

export default useKeyboardShortcuts