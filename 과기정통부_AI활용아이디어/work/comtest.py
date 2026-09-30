import win32com.client as w, os, sys
src=os.path.abspath(sys.argv[1]); out=os.path.abspath(sys.argv[2]); fmt=sys.argv[3]
h=w.gencache.EnsureDispatch("HWPFrame.HwpObject")
try: h.RegisterModule("FilePathCheckDLL","FilePathCheckerModule")
except Exception as e: print("reg",e)
h.XHwpWindows.Item(0).Visible=False
print(h.Open(src,"","forceopen:true"))
print(h.SaveAs(out,fmt,""))
h.Clear(1); h.Quit()
