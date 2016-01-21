""" Configurable. Eternal loop. Read data. Write data. """
from common import *


default_data = None

def setup(data = default_data):
    import wx
    dlg = wx.TextEntryDialog(
        None, 'Data value?',
        'Configure Process', str(data))
    if dlg.ShowModal() == wx.ID_OK:
        try:
            data = eval(dlg.GetValue())
        except:
            data = dlg.GetValue()
    dlg.Destroy()
    return data

def agentFunc(in0,in1,out0,out1 , data = default_data):
    while True:
        val0 = in0()
        val1 = in1()

        #Insert work here

        out0(result0)
        out1(result1)

