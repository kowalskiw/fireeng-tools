import PySimpleGUI as psg


def simple_gui():
    for i in range(2):
        tab_layout1 = [[psg.Text('Path:', size=(5, 1)), psg.InputText(), psg.FolderBrowse('Choose')],
                       [psg.Text('Vent-start time:', size=(14, 1), key=i), psg.InputText(size=(4, 0), key=i)],
                       [psg.Text('Evac-end time:', size=(14, 1)), psg.InputText(size=(4, 0), key=i)],
                       [psg.Text('Response time:', size=(14, 1)), psg.InputText(size=(4, 0), key=i)],
                       ]

    layout = [[psg.TabGroup([[psg.Tab('Scenario 1', tab_layout1), psg.Tab('Scenario 2', tab_layout1)]])],
              [psg.Submit(), psg.Cancel()]
              ]

    window = psg.Window('Generator').Layout(layout)
    button, values = window.Read()

    if button == 'Submit':
        return values
    else:
        exit()


print(simple_gui())
