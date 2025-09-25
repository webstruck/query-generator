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
}

export const useKeyboardShortcuts = ({ 
  shortcuts, 
  enabled = true
}: UseKeyboardShortcutsOptions) => {
  
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return

    // Check if we should ignore this event based on focused element
    const activeElement = document.activeElement
    if (activeElement) {
      // Only ignore shortcuts for text input elements where typing is expected
      const isTextInput = (
        (activeElement.tagName.toLowerCase() === 'input' && 
         ['text', 'email', 'password', 'search', 'url', 'number'].includes((activeElement as HTMLInputElement).type)) ||
        activeElement.tagName.toLowerCase() === 'textarea' ||
        activeElement.hasAttribute('contenteditable')
      )
      
      // For text input elements, only allow modifier-key shortcuts
      if (isTextInput) {
        const hasModifierKey = event.metaKey || event.ctrlKey || event.altKey
        if (!hasModifierKey) {
          return // Block single-key shortcuts only for text input elements
        }
      }
      
      // For all other elements (checkboxes, buttons, selects, etc.), allow all shortcuts
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
  }, [shortcuts, enabled])

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
  if (event.metaKey) pressedKeys.push('⌘')
  if (event.ctrlKey) pressedKeys.push('^')
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