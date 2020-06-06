# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QFileDialog
from PyQt5.QtWidgets import QMessageBox, QGroupBox, QSpinBox, QProgressBar
from PyQt5.QtWidgets import QMenu, QCheckBox
from PyQt5.QtGui import QPixmap, QIcon, QFont
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtCore import QAbstractNativeEventFilter
import ff14midi
import _thread
import win32gui, win32api
import ntplib
import hashlib
import time
import configparser
import ctypes.wintypes

programBasePath = None

def getResourcePath(path):
    global programBasePath
    if(programBasePath is None):
        programBasePath = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(programBasePath, path)   
       
def nullWheelEvent(e):
    pass

class MainWindow(QWidget):
    
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.version = '1.0'
        self.baseTitle = '『克拉维亚·吹小曲儿』'
        self.lastOpenDirPath = '.'
        self.setWindowTitle(self.baseTitle)
        self.setWindowIcon(QIcon(getResourcePath('icon.png')))
        self.resize(700, 300)
        self.setFont(QFont('微软雅黑', 10))

        vbox = QVBoxLayout()
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Midi文件:'), 5)
        self.midiFileHash = ''
        self.lblFileName = QLabel('还没选')
        hbox.addWidget(self.lblFileName, 50)
        pb = QPushButton('选文件')
        pb.clicked.connect(self.chooseMidiFile)
        hbox.addWidget(pb, 1)
        vbox.addLayout(hbox)
        
        hbox = QHBoxLayout()
        pb = QPushButton('刷新游戏窗口')
        pb.clicked.connect(self.refreshGameProcess)
        hbox.addWidget(pb)   
        vbox.addLayout(hbox)
        
        hbox1 = QHBoxLayout()
        
        gb = QGroupBox('左边的游戏客户端')
        vbox1 = QVBoxLayout()
        self.lblGame0 = QLabel('没有')
        vbox1.addWidget(self.lblGame0)
        hbox2 = QHBoxLayout()
        pb = QPushButton('测试')
        pb.clicked.connect(self.gameTest0)
        hbox2.addWidget(pb)
        pb = QPushButton('测试键位')
        pb.clicked.connect(self.testKeyMap)
        hbox2.addWidget(pb)
        vbox1.addLayout(hbox2)
        cb = QCheckBox('使用Midi键盘')
        cb.stateChanged.connect(self.useMidiKeyboardFor0)
        vbox1.addWidget(cb)
        gb.setLayout(vbox1)
        hbox1.addWidget(gb)
        
        gb = QGroupBox('右边的游戏客户端')
        vbox1 = QVBoxLayout()
        self.lblGame1 = QLabel('没有')
        vbox1.addWidget(self.lblGame1)
        pb = QPushButton('测试')
        pb.clicked.connect(self.gameTest1)
        vbox1.addWidget(pb)
        cb = QCheckBox('使用Midi键盘')
        cb.stateChanged.connect(self.useMidiKeyboardFor1)
        vbox1.addWidget(cb)
        gb.setLayout(vbox1)
        hbox1.addWidget(gb)
        
        vbox.addLayout(hbox1)
       
        hbox = QHBoxLayout()
        
        gb = QGroupBox('单人/双开 演奏')
        vbox1 = QVBoxLayout()
        pb = QPushButton('用Midi键盘弹琴')
        pb.clicked.connect(self.useMidiKeybord)
        vbox1.addWidget(pb)
        pb = QPushButton('双开而且Midi键盘很长')
        pb.clicked.connect(self.useMidiKeybordToTwoGames)
        vbox1.addWidget(pb)
        pb = QPushButton('直接开始Midi文件')
        pb.setIcon(QIcon(getResourcePath('iconPlay.png')))
        pb.clicked.connect(self.begin)
        vbox1.addWidget(pb)
        gb.setLayout(vbox1)
        hbox.addWidget(gb, 1)
        
        gb = QGroupBox('节拍器同步合奏')
        vbox1 = QVBoxLayout()     
        hbox1 = QHBoxLayout()
        hbox1.addWidget(QLabel('X:'), 1)
        self.sbMetronomeX = QSpinBox()
        self.sbMetronomeX.setMinimum(1)
        self.sbMetronomeX.setMaximum(1000)
        self.sbMetronomeX.setValue(59)
        self.sbMetronomeX.wheelEvent = nullWheelEvent
        hbox1.addWidget(self.sbMetronomeX, 5)
        hbox1.addWidget(QLabel('Y:'), 1)
        self.sbMetronomeY = QSpinBox()
        self.sbMetronomeY.setMinimum(1)
        self.sbMetronomeY.setMaximum(1000)
        self.sbMetronomeY.setValue(110)
        self.sbMetronomeY.wheelEvent = nullWheelEvent
        hbox1.addWidget(self.sbMetronomeY, 5)
        vbox1.addLayout(hbox1)
        hbox1 = QHBoxLayout()
        pb = QPushButton('检查节拍器坐标')
        pb.clicked.connect(self.checkMetronome)
        hbox1.addWidget(pb)
        pb = QPushButton('节拍器回放')
        pb.clicked.connect(self.metronomeEcho)
        hbox1.addWidget(pb)
        vbox1.addLayout(hbox1)
        gb.setLayout(vbox1)
        pb = QPushButton('等待节拍器信号')
        pb.setIcon(QIcon(getResourcePath('iconPlay.png')))
        pb.clicked.connect(self.waitMetronome)
        vbox1.addWidget(pb)
        hbox.addWidget(gb, 1)       
        
        gb = QGroupBox('定时同步合奏')
        vbox1 = QVBoxLayout()
        
        gb.setLayout(vbox1)
        hbox.addWidget(gb, 1)
        
        hbox1 = QHBoxLayout()
        self.lblSyncTime = QLabel()
        hbox1.addWidget(self.lblSyncTime)
        vbox1.addLayout(hbox1)
        hbox1 = QHBoxLayout()
        tt = time.localtime()
        self.sbSetHour = QSpinBox()
        self.sbSetHour.setMinimum(0)
        self.sbSetHour.setMaximum(23)
        self.sbSetHour.setValue(tt.tm_hour)
        self.sbSetHour.wheelEvent = nullWheelEvent
        hbox1.addWidget(self.sbSetHour)
        hbox1.addWidget(QLabel(':'))
        self.sbSetMinute = QSpinBox()
        self.sbSetMinute.setMinimum(0)
        self.sbSetMinute.setMaximum(59)
        self.sbSetMinute.setValue(tt.tm_min)
        self.sbSetMinute.wheelEvent = nullWheelEvent
        hbox1.addWidget(self.sbSetMinute)
        hbox1.addWidget(QLabel(':'))
        self.sbSetSecond = QSpinBox()
        self.sbSetSecond.setMinimum(0)
        self.sbSetSecond.setMaximum(59)
        self.sbSetSecond.setValue(0)
        self.sbSetSecond.wheelEvent = nullWheelEvent
        hbox1.addWidget(self.sbSetSecond)
        vbox1.addLayout(hbox1)
        pb = QPushButton('定时开始')
        pb.setIcon(QIcon(getResourcePath('iconPlay.png')))
        pb.clicked.connect(self.beginAtTime)
        vbox1.addWidget(pb)
        
        vbox.addLayout(hbox)
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('离下一个音还有(秒):'))
        self.lblTimeToNextNote = QLabel()
        hbox.addWidget(self.lblTimeToNextNote)
        hbox.addWidget(QLabel('推迟演奏时间(毫秒):'))
        self.sbDelay = QSpinBox()
        self.sbDelay.setMinimum(-10000)
        self.sbDelay.setMaximum(10000)
        self.sbDelay.setValue(0)
        self.sbDelay.setSingleStep(10)
        self.sbDelay.valueChanged.connect(self.changeDelay)
        self.sbDelay.wheelEvent = nullWheelEvent
        hbox.addWidget(self.sbDelay)
        vbox.addLayout(hbox)
        
        hbox = QHBoxLayout()
        pb = QPushButton('停止')
        pb.setIcon(QIcon(getResourcePath('iconStop.png')))
        pb.clicked.connect(self.stop)
        hbox.addWidget(pb)
        vbox.addLayout(hbox)
                
        vbox.addStretch()
        
        self.pbProgress = QProgressBar()
        self.pbProgress.setMinimum(0)
        vbox.addWidget(self.pbProgress)
               
        hboxMain = QHBoxLayout()
        hboxMain.addLayout(vbox, 100)
               
        vbox = QVBoxLayout()
        
        self.logo = QLabel()
        self.pmLogo = QPixmap(getResourcePath('logo.png'))
        self.pmLogoIdle = QPixmap(getResourcePath('logoIdle.png'))
        self.logo.setPixmap(self.pmLogoIdle)
        self.logo.contextMenuEvent = self.logoMenu
        self.logoIsIdle = True
        vbox.addWidget(self.logo, 1)
                
        hboxMain.addLayout(vbox, 1)
        
        self.setLayout(hboxMain)
        
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        try:
            self.lastOpenDirPath = self.config['params']['lastOpenDir']
        except:
            pass
        try:
            self.sbMetronomeX.setValue(int(self.config['params']['metronomeX']))
        except:
            pass
        try:
            self.sbMetronomeY.setValue(int(self.config['params']['metronomeY']))
        except:
            pass
        try:
            self.sbDelay.setValue(int(self.config['params']['delay']))
        except:
            pass
        self.ntpServers = ['ntp3.aliyun.com', 'time.windows.com']
    
        self.show()
        
        if(not ff14midi.loadKeyMap('keyMap.txt')):
            QMessageBox.warning(self, '错误', '无法读取键位设置。')
        self.timeOffset = 0.0
        self.refreshGameProcess()

        self.timeSynced = False
        _thread.start_new_thread(self.syncTime, ())

        self.statusTimer = QTimer()
        self.statusTimer.timeout.connect(self.updateStatus)
        self.statusTimer.start(1000)
        
        self.midiFileContent = None
    
    def getRemoteTime(self):
        i = 0
        for _ in range(6):
            try:
                ntp = ntplib.NTPClient()
                ret = ntp.request(self.ntpServers[i])
                return ret.tx_time
            except:
                ff14midi.log('Unable to get remote time.')
                i = (i + 1) % len(self.ntpServers)
        return None      
                
    def chooseMidiFile(self):
        filePath = QFileDialog.getOpenFileName(self, '选择Midi文件', self.lastOpenDirPath, 'Midi文件 (*.mid)')[0]
        if(filePath == ''):
            return
        self.lastOpenDirPath = os.path.dirname(filePath)
        f = open(filePath, 'rb')
        self.midiFileContent = f.read()
        self.midiFileHash = hashlib.md5(self.midiFileContent).hexdigest()[-8:]
        self.midiFileName = os.path.basename(filePath)
        f.close()
        file = filePath
        self.lblFileName.setText(self.midiFileName + ' [校验码:' + self.midiFileHash + ']')
        ff14midi.loadMidi(file)
        ff14midi.log('Loaded midi file from: ' + filePath)
            
    def refreshGameProcess(self):
        ff14midi.updateWindowHandles()
        if(len(ff14midi.ff14WindowHandle) > 0):
            self.lblGame0.setText('窗口:' + str(ff14midi.ff14WindowHandle[0]))
            if(len(ff14midi.ff14WindowHandle) > 1):
                self.lblGame1.setText('窗口:' + str(ff14midi.ff14WindowHandle[1]))
            else:
                self.lblGame1.setText('没有')
        else:
            self.lblGame0.setText('没有')
            self.lblGame1.setText('没有')        
        
    def gameTest(self, hid):
        try:
            if(hid < len(ff14midi.ff14WindowHandle)):
                ff14midi.keyPress(hid, ff14midi.keyCode[12])
        except:
            pass
    
    def gameTest0(self):
        self.gameTest(0)
        
    def gameTest1(self):
        self.gameTest(1)
        
    def testKeyMap(self):
        if(len(ff14midi.ff14WindowHandle) == 0):
            return
        if((ff14midi.isPlaying) or (ff14midi.isPerforming)):
            QMessageBox.warning(self, '正在演奏', '已经在演奏了。')
            return
        _thread.start_new_thread(ff14midi.checkKeyMap, ())
        
    def useMidiKeybord(self):
        if((ff14midi.isPlaying) or (ff14midi.isPerforming)):
            QMessageBox.warning(self, '正在演奏', '已经在演奏了。')
            return
        _thread.start_new_thread(ff14midi.playMidiInput, ())
        
    def useMidiKeybordToTwoGames(self):
        if((ff14midi.isPlaying) or (ff14midi.isPerforming)):
            QMessageBox.warning(self, '正在演奏', '已经在演奏了。')
            return
        _thread.start_new_thread(ff14midi.playMidiInputToTwoGames, ())
        
    def useMidiKeyboardFor0(self, state):
        ff14midi.sendMidiInput[0] = state == Qt.Checked
    
    def useMidiKeyboardFor1(self, state):
        ff14midi.sendMidiInput[1] = state == Qt.Checked
        
    def begin(self, mode='', prefixNoteId=0):
        if((ff14midi.isPlaying) or (ff14midi.isPerforming)):
            QMessageBox.warning(self, '正在演奏', '已经在演奏了。')
            return
        if(ff14midi.mid is None):
            QMessageBox.warning(self, '没内容', '还没选Midi文件。')
            return
        _thread.start_new_thread(ff14midi.play, (mode,))
    
    def updateStatus(self):
        self.lblSyncTime.setText(time.strftime('%H:%M:%S', time.localtime(time.time() + self.timeOffset)))
        self.pbProgress.setMaximum(ff14midi.seqLength)
        self.pbProgress.setValue(ff14midi.progress)
        if(ff14midi.timeToNextNote > 100000):
            self.lblTimeToNextNote.setText('-')
        else:
            self.lblTimeToNextNote.setText(str(int(ff14midi.timeToNextNote)))
        if(((ff14midi.isPlaying) or (ff14midi.isPerforming)) and self.logoIsIdle):
            self.logoIsIdle = False
            self.logo.setPixmap(self.pmLogo)
        elif((not ((ff14midi.isPlaying) or (ff14midi.isPerforming))) and (not self.logoIsIdle)):
            self.logoIsIdle = True
            self.logo.setPixmap(self.pmLogoIdle)
    
    def waitMetronome(self):
        ff14midi.metronomeX = self.sbMetronomeX.value()
        ff14midi.metronomeY = self.sbMetronomeY.value()
        ff14midi.startFromIndex = 0
        self.begin(mode='metronome')
        
    def beginAtTime(self):
        tt = time.localtime()
        ff14midi.scheduledBeginTime = time.mktime((tt.tm_year, tt.tm_mon, tt.tm_mday,
            self.sbSetHour.value(), self.sbSetMinute.value(), self.sbSetSecond.value(), 0, 0, 0)) - self.timeOffset
        if(ff14midi.scheduledBeginTime < time.time()):
            QMessageBox.warning(self, '时间不对', '设定的时间已经过了。')
            return
        ff14midi.log('Scheduled begin local time ' + str(ff14midi.scheduledBeginTime))
        ff14midi.startFromIndex = 0
        self.begin(mode='time')
        
    def changeDelay(self, delay):
        ff14midi.delay = delay * 0.001
        
    def metronomeEcho(self):
        ff14midi.metronomeX = self.sbMetronomeX.value()
        ff14midi.metronomeY = self.sbMetronomeY.value()
        if((ff14midi.isPlaying) or (ff14midi.isPerforming)):
            QMessageBox.warning(self, '正在演奏', '已经在演奏了。')
            return
        _thread.start_new_thread(ff14midi.metronomeEcho, ())       
    
    def stop(self):
        ff14midi.terminating = True
        
    def checkMetronome(self):
        if(len(ff14midi.ff14WindowHandle) == 0):
            QMessageBox.warning(self, '没游戏', '先启动游戏啦。')
            return
        rect = win32gui.GetWindowRect(ff14midi.ff14WindowHandle[0])
        x = rect[0] + self.sbMetronomeX.value()
        y = rect[1] + self.sbMetronomeY.value()
        win32api.SetCursorPos((x, y))

    def syncTime(self):
        i = 0
        while(True):
            try:
                ff14midi.log('Synchronizing time.')
                ntp = ntplib.NTPClient()
                ret = ntp.request(self.ntpServers[i])
                self.timeOffset = ret.offset
                ff14midi.log('Local time offset: ' + str(ret.offset))
                self.timeSynced = True
                return
            except:
                ff14midi.log('Unable to synchronize time.')
                i = (i + 1) % len(self.ntpServers)
    
    def logoMenu(self, event):
        menu = QMenu(self)
        aboutAction = menu.addAction('关于本软件(' + self.version + ')')
        action = menu.exec_(self.logo.mapToGlobal(event.pos()))
        if(action == aboutAction):
            QMessageBox.information(self, '关于本软件', '延夏的Clavy好胖！')
                
    def saveConfig(self):
        self.config.read('config.ini')
        if(not 'params' in self.config):
            self.config['params'] = {}
        self.config['params']['lastOpenDir'] = self.lastOpenDirPath
        self.config['params']['metronomeX'] = str(self.sbMetronomeX.value())
        self.config['params']['metronomeY'] = str(self.sbMetronomeY.value())
        f = open('config.ini', 'w')
        self.config.write(f)
        f.close()

class WinEventFilter(QAbstractNativeEventFilter):
    def __init__(self, mw):
        QAbstractNativeEventFilter.__init__(self)
        self.mw = mw
    def nativeEventFilter(self, eventType, message):
        if(eventType != 'windows_generic_MSG'):
            return False, 0
        msg = ctypes.wintypes.MSG.from_address(message.__int__())
        if(msg.message == 1024):
            if(msg.wParam == 8122):
                self.mw.begin()
                ff14midi.log('Triggered begin by system message.')
            elif(msg.wParam == 8123):
                self.mw.stop()
                ff14midi.log('Triggered stop by system message.')
            elif(msg.wParam == 8124):
                self.mw.sbDelay.setValue(self.mw.sbDelay.value() + int(msg.lParam))
                ff14midi.log('Delay is added by ' + str(msg.lParam / 1000) + ' by system message.')
        return False, 0


app = None
if(__name__ == '__main__'):
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        app = QApplication(sys.argv)
        mw = MainWindow()
        wef = WinEventFilter(mw)
        app.installNativeEventFilter(wef)
        app.exec_()
        mw.saveConfig()
    except Exception as e:
        print(e)
        input()