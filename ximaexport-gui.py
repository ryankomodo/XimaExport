#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
GUI for ximaexport.py

- Bulk export downloaded audios in Ximalaya.
- Auto rename exported audios using a configurable format.
- Create folders for albums, named using album names, and save audios correspondingly.

# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-07-12 11:18:42.
'''


import sys,os
from ttk import Style, Combobox
from tkFileDialog import askopenfilename, askdirectory
import tkMessageBox
import ximaexport
import Queue
import threading
import sqlite3
import pandas as pd
if sys.version_info[0]>=3:
    import tkinter as tk
    from tkinter import Frame
else:
    import Tkinter as tk
    from Tkinter import Frame


stdout=sys.stdout

def printch(x):
    print(x.decode('gbk'))
dgbk=lambda x: x.decode('gbk')


class Redirector(object):
    def __init__(self,q):
        self.q=q

    def write(self,string):
        self.q.put(string)

    '''
    def flush(self):
        with self.q.mutex:
            self.q.queue.clear()
    '''




class WorkThread(threading.Thread):
    def __init__(self,name,exitflag,stateq):
        threading.Thread.__init__(self)
        self.name=name
        self.exitflag=exitflag
        self._stop=threading.Event()
        self.stateq=stateq

    def run(self):
        #print('\nStart processing...')
        printch('\n开始处理...')
        if not self._stop.is_set():
            ximaexport.main(*self.args)
            self.stateq.put('done')

    def stop(self):
        self.exitflag=True
        self._stop.set()



class MainFrame(Frame):
    def __init__(self,parent,stdoutq):
        Frame.__init__(self,parent)

        self.parent=parent
        self.width=750
        self.height=450
        self.title=ximaexport.__version__
        self.stdoutq=stdoutq
        
        self.initUI()

        self.hasdb=False
        self.hasout=False
        self.exit=False

        self.path_frame=self.addPathFrame()
        self.action_frame=self.addActionFrame()
        self.message_frame=self.addMessageFrame()
        self.printStr()

        self.stateq=Queue.Queue()


    def centerWindow(self):
        sw=self.parent.winfo_screenwidth()
        sh=self.parent.winfo_screenheight()
        x=(sw-self.width)/2
        y=(sh-self.height)/2
        self.parent.geometry('%dx%d+%d+%d' \
                %(self.width,self.height,x,y))


    def initUI(self):
        self.parent.title(self.title)
        self.style=Style()
        #Choose from default, clam, alt, classic
        self.style.theme_use('alt')
        self.pack(fill=tk.BOTH,expand=True)
        self.centerWindow()


    def printStr(self):
        while self.stdoutq.qsize() and self.exit==False:
            try:
                msg=self.stdoutq.get()
                self.text.update()
                self.text.insert(tk.END,msg)
                self.text.see(tk.END)
            except Queue.Empty:
                pass
        self.after(100,self.printStr)



    def checkReady(self):

        if self.hasdb and self.hasout:
            self.start_button.configure(state=tk.NORMAL)
            #print('XimaExport Ready.')
            printch('XimaExport 就绪.')
        else:
            self.start_button.configure(state=tk.DISABLED)


    def addPathFrame(self):
        frame=Frame(self)
        frame.pack(fill=tk.X,expand=0,side=tk.TOP,padx=8,pady=5)

        frame.columnconfigure(1,weight=1)

        #------------------Database file------------------
        label=tk.Label(frame,text=dgbk('ting.sqlite文件:'),\
                bg='#bbb')
        label.grid(row=0,column=0,\
                sticky=tk.W,padx=8)

        self.db_entry=tk.Entry(frame)
        self.db_entry.grid(row=0,column=1,sticky=tk.W+tk.E,padx=8)

        self.db_button=tk.Button(frame,text=dgbk('打开'),command=self.openFile)
        self.db_button.grid(row=0,column=2,padx=8,sticky=tk.E)

        #--------------------Output dir--------------------
        label2=tk.Label(frame,text=dgbk('导出到文件夹:'),\
                bg='#bbb')
        label2.grid(row=2,column=0,\
                sticky=tk.W,padx=8)

        self.out_entry=tk.Entry(frame)
        self.out_entry.grid(row=2,column=1,sticky=tk.W+tk.E,padx=8)
        self.out_button=tk.Button(frame,text=dgbk('选择'),command=self.openDir)
        self.out_button.grid(row=2,column=2,padx=8,sticky=tk.E)
        


    def openDir(self):
        self.out_entry.delete(0,tk.END)
        dirname=askdirectory()
        self.out_entry.insert(tk.END,dirname)
        if len(dirname)>0:
            #print('Output folder: %s' %dirname)
            printch('输出到文件夹:')
	    print('   '+dirname)
            self.hasout=True
            self.checkReady()


    def openFile(self):
        self.db_entry.delete(0,tk.END)
        ftypes=[('sqlite files','*.sqlite'),('ALL files','*')]
        filename=askopenfilename(filetypes=ftypes)
        self.db_entry.insert(tk.END,filename)
        if len(filename)>0:
            #print('Database file: %s' %filename)
            printch('数据文件:')
	    print('   '+filename)
            self.probeAlbums()


    def probeAlbums(self):
        dbfile=self.db_entry.get()
        try:
            db=sqlite3.connect(dbfile)
            df=ximaexport.getData(db)
            self.albumlist=ximaexport.getAlbumList(df,None)   #(id, name)
            self.albumnames=['All']+[ii[1] for ii in self.albumlist] #names to display
            self.albummenu['values']=tuple(self.albumnames)
            self.albummenu.current(0)
            db.close()

            self.hasdb=True
            self.checkReady()

        except Exception as e:
            #print('Failed to recoganize the given database file.') 
            printch('无法识别sqlite数据文件.') 
            print(e)



    
    def addActionFrame(self):

        frame=Frame(self,relief=tk.RAISED,borderwidth=1)
        frame.pack(fill=tk.X,side=tk.TOP,\
                expand=0,padx=8,pady=5)

        #label=tk.Label(frame,text='Actions:',bg='#bbb')
        #label.grid(row=0,column=0,sticky=tk.W,padx=8)

        #---------------Action checkbuttons---------------
        frame.columnconfigure(0,weight=1)

        #---------------------2nd row---------------------
        subframe=Frame(frame)
        subframe.grid(row=1,column=0,columnspan=6,sticky=tk.W+tk.E,\
                pady=5)

        #-------------------Album options-------------------
        albumlabel=tk.Label(subframe,text=dgbk('专辑:'),\
                bg='#bbb')
        albumlabel.pack(side=tk.LEFT, padx=8)

        self.album=tk.StringVar()
        self.albumnames=['All',]
        self.albummenu=Combobox(subframe,textvariable=\
                self.album,values=self.albumnames,state='readonly')
        self.albummenu.current(0)
        self.albummenu.bind('<<ComboboxSelected>>',self.setAlbum)
        self.albummenu.pack(side=tk.LEFT,padx=8)
        
        #-------------------Quit button-------------------
        quit_button=tk.Button(subframe,text=dgbk('退出'),\
                command=self.quit)
        quit_button.pack(side=tk.RIGHT,padx=8)

        #-------------------Stop button-------------------
        '''
        self.stop_button=tk.Button(subframe,text='Stop',\
                command=self.stop)
        self.stop_button.pack(side=tk.RIGHT,padx=8)
        '''
                
        #-------------------Start button-------------------
        self.start_button=tk.Button(subframe,text=dgbk('开始'),\
                command=self.start,state=tk.DISABLED)
        self.start_button.pack(side=tk.RIGHT,pady=8)

        #-------------------Help button-------------------
        self.help_button=tk.Button(subframe,text=dgbk('帮助'),\
                command=self.showHelp)
        self.help_button.pack(side=tk.RIGHT,padx=8)





    def setAlbum(self,x):
	import json
        self.albummenu.selection_clear()
        self.album=self.albummenu.get()
        self.albummenu.set(self.album)
        if self.album=='All':
            #print('Work on all albums.')
            printch('导出所有专辑.')
        else:
            #print('Select album: '+self.album)
            printch('导出所选专辑:')
	    print('   '+self.album)





    def showHelp(self):
        helpstr=dgbk('''\n\n
导出喜马拉雅下载音频，并自动按专辑归档、重命名：\n
1. 找到手机/pad中的喜马拉雅数据文件夹：\n
    （1）苹果用户：链接电脑itunes，在app一栏中找到“喜马拉雅”，单击，右侧会出现“喜马拉雅”的数据文件。选择“iDoc”，并导出到电脑。\n
    （2）安卓用户：链接电脑后，拷贝出ting文件夹。\n
2. 运行ximaexport-gui.exe。\n
    在 “ting.sqlite文件”一栏，选择步骤1中拷贝出的文件夹里的 ting.sqlite. 文件。\n
    在 “导出到文件夹”一栏，选择音频存储位置。\n
    在 “专辑”下拉菜单，选择要导出的专辑。若全部导出选择“All”。\n
    点击“开始”开始处理。
''')

        tkMessageBox.showinfo(title='Help', message=helpstr)
        #print(self.menfolder.get())



    def start(self):
        dbfile=self.db_entry.get()
        outdir=self.out_entry.get()
        self.album=self.albummenu.get()

        self.out_button.configure(state=tk.DISABLED)
        self.start_button.configure(state=tk.DISABLED)
        self.help_button.configure(state=tk.DISABLED)
        self.albummenu.configure(state=tk.DISABLED)
        self.messagelabel.configure(text=dgbk('信息 (处理中...)'))

        album=None if self.album=='All' else self.album

        args=[dbfile,outdir,album,True]

        self.workthread=WorkThread('work',False,self.stateq)
        self.workthread.deamon=True

        self.workthread.args=args
        self.workthread.start()
        self.reset()


    def reset(self):
        while self.stateq.qsize() and self.exit==False:
            try:
                msg=self.stateq.get()
                if msg=='done':
                    self.db_button.configure(state=tk.NORMAL)
                    self.out_button.configure(state=tk.NORMAL)
                    self.start_button.configure(state=tk.NORMAL)
                    self.help_button.configure(state=tk.NORMAL)
                    self.albummenu.configure(state='readonly')
                    self.messagelabel.configure(text=dgbk('消息'))
                    return
            except Queue.Empty:
                pass
        self.after(100,self.reset)


    
    def stop(self):
        #self.workthread.stop()
        pass
        

    def addMessageFrame(self):
        frame=Frame(self)
        frame.pack(fill=tk.BOTH,side=tk.TOP,\
                expand=1,padx=8,pady=5)

        self.messagelabel=tk.Label(frame,text=dgbk('消息'),bg='#bbb')
        self.messagelabel.pack(side=tk.TOP,fill=tk.X)

        self.text=tk.Text(frame)
        self.text.pack(side=tk.TOP,fill=tk.BOTH,expand=1)
        self.text.height=10

        scrollbar=tk.Scrollbar(self.text)
        scrollbar.pack(side=tk.RIGHT,fill=tk.Y)

        self.text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text.yview)

        


def main():

    stdoutq=Queue.Queue()
    sys.stdout=Redirector(stdoutq)

    root=tk.Tk()
    mainframe=MainFrame(root,stdoutq)
    mainframe.pack()

    root.mainloop()


if __name__=='__main__':
    main()


