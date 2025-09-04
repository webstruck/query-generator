import React from 'react'
import { ButtonWithShortcut } from '../ui/button-with-shortcut'
import { KeyboardShortcut, KEYBOARD_SHORTCUTS } from '../ui/keyboard-shortcut'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

export const KeyboardShortcutDemo: React.FC = () => {
  return (
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Keyboard Shortcuts Demo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          
          {/* Individual Shortcut Display */}
          <div>
            <h3 className="text-lg font-medium mb-3">Individual Shortcuts</h3>
            <div className="flex flex-wrap gap-4">
              <KeyboardShortcut keys={['A']} />
              <KeyboardShortcut keys={['⌘', 'S']} />
              <KeyboardShortcut keys={['⌘', '⇧', 'Z']} />
              <KeyboardShortcut keys={['Esc']} />
              <KeyboardShortcut keys={['←']} />
              <KeyboardShortcut keys={['→']} />
            </div>
          </div>

          {/* Buttons with Shortcuts - End Placement */}
          <div>
            <h3 className="text-lg font-medium mb-3">Buttons with Shortcuts (End Placement)</h3>
            <div className="flex flex-wrap gap-3">
              <ButtonWithShortcut shortcut="approve" className="bg-green-600 text-white hover:bg-green-700">
                Approve
              </ButtonWithShortcut>
              <ButtonWithShortcut shortcut="reject" className="bg-red-600 text-white hover:bg-red-700">
                Reject  
              </ButtonWithShortcut>
              <ButtonWithShortcut shortcut="edit" variant="outline">
                Edit
              </ButtonWithShortcut>
              <ButtonWithShortcut shortcut="save" variant="default">
                Save
              </ButtonWithShortcut>
            </div>
          </div>

          {/* Buttons with Shortcuts - Start Placement */}
          <div>
            <h3 className="text-lg font-medium mb-3">Buttons with Shortcuts (Start Placement)</h3>
            <div className="flex flex-wrap gap-3">
              <ButtonWithShortcut shortcut="approve" shortcutPlacement="start" className="bg-green-600 text-white hover:bg-green-700">
                Approve
              </ButtonWithShortcut>
              <ButtonWithShortcut shortcut="next" shortcutPlacement="start" variant="outline">
                Next
              </ButtonWithShortcut>
              <ButtonWithShortcut shortcut="previous" shortcutPlacement="start" variant="outline">
                Previous
              </ButtonWithShortcut>
            </div>
          </div>

          {/* Buttons with Shortcuts - Below Placement */}
          <div>
            <h3 className="text-lg font-medium mb-3">Buttons with Shortcuts (Below Placement)</h3>
            <div className="flex flex-wrap gap-4">
              <ButtonWithShortcut shortcut="option1" shortcutPlacement="below" variant="outline">
                Yes
              </ButtonWithShortcut>
              <ButtonWithShortcut shortcut="option2" shortcutPlacement="below" variant="outline">
                No
              </ButtonWithShortcut>
            </div>
          </div>

          {/* All Available Shortcuts Reference */}
          <div>
            <h3 className="text-lg font-medium mb-3">All Available Shortcuts</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 text-sm">
              {Object.entries(KEYBOARD_SHORTCUTS).map(([key, shortcuts]) => (
                <div key={key} className="flex items-center justify-between p-2 border rounded">
                  <span className="capitalize">{key}</span>
                  <KeyboardShortcut keys={[...shortcuts]} />
                </div>
              ))}
            </div>
          </div>

        </CardContent>
      </Card>
    </div>
  )
}