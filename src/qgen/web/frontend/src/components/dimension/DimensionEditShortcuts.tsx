import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface DimensionEditShortcutsProps {
  isActive: boolean
  isEditing: boolean
  onStartEdit: () => void
  onSave: () => void
  onCancel: () => void
}

export const DimensionEditShortcuts: React.FC<DimensionEditShortcutsProps> = ({
  isActive,
  isEditing,
  onStartEdit,
  onSave,
  onCancel
}) => {
  useKeyboardShortcuts({
    shortcuts: [
      { keys: ['E'], handler: onStartEdit, description: 'Edit dimensions', enabled: isActive && !isEditing },
      { keys: ['^', 'S'], handler: onSave, description: 'Save dimensions', enabled: isActive && isEditing },
      { keys: ['Esc'], handler: onCancel, description: 'Cancel editing', enabled: isActive && isEditing }
    ],
    enabled: isActive
  })

  return null // This component only provides keyboard shortcuts
}