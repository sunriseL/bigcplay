# -*- coding: utf-8 -*-
import win32gui
import win32con
import win32api
import time
import mido
import ctypes
import _thread

ff14WindowHandle = []
keyCode = {}
sequence = []
minNoteLength = 0.01
sameSpacing = 0.051
differentSpacing = 0.051
mid = None
isPlaying = False
isPerforming = False
terminating = False
metronomeX = 0
metronomeY = 0
delay = 0
progress = 0
seqLength = 1
scheduledBeginTime = 0
sendMidiInput = [False, False]
useMidiDevice = ['默认', '默认']
timeToNextNote = 1000000

def log(text):
    print('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + '] ' + text)

def getDevices():
    return mido.get_input_names()

def enumWindowCallback(hwnd, lParam):
    global ff14WindowHandle
    if(win32gui.GetWindowText(hwnd) == '最终幻想XIV'):
        ff14WindowHandle.append(hwnd)
        
def updateWindowHandles():
    global ff14WindowHandle
    ff14WindowHandle = []
    win32gui.EnumWindows(enumWindowCallback, None)
    if(len(ff14WindowHandle) > 1):
        rect0 = win32gui.GetWindowRect(ff14WindowHandle[0])
        rect1 = win32gui.GetWindowRect(ff14WindowHandle[1])
        if(rect0[0] > rect1[0]):
            h = ff14WindowHandle[0]
            ff14WindowHandle[0] = ff14WindowHandle[1]
            ff14WindowHandle[1] = h
    log('Found FF14 windows: ' + str(ff14WindowHandle))

def keyDown(hid, keyCode):
    global ff14WindowHandle
    try:
        win32api.PostMessage(ff14WindowHandle[hid], win32con.WM_KEYDOWN, keyCode, 0)
    except:
        pass

def keyUp(hid, keyCode):
    global ff14WindowHandle
    try:
        win32api.PostMessage(ff14WindowHandle[hid], win32con.WM_KEYUP, keyCode, 0)
    except:
        pass

def keyPress(hid, keyCode, timeLength=0.1):
    keyDown(hid, keyCode)
    time.sleep(timeLength)
    keyUp(hid, keyCode)

def loadKeyMap(filePath):
    global keyCode
    try:
        f = open(filePath)
        content = f.read()
        keyCode = []
        for c in content:
            keyCode.append(ctypes.windll.User32.VkKeyScanA(ord(c)) & 0xffff)
        f.close()
        log('Loaded key map: ' + str(keyCode))
    except:
        log('Cannot load key map from file.')
        return False
    return True

def processTrack(track, tid, offset):
    global sequence, bpms, tpb
    bpmIndex = 0
    bpm = bpms[0][1]
    sequence.append([tid, -2, None, True, 0])
    sequence.append([tid, -1, None, True, 0])
    noteTick = 0
    noteTime = 0
    for msg in track:
        lastTick = noteTick
        noteTick += msg.time
        while(noteTick >= bpms[bpmIndex+1][0]):
            bpmIndex += 1
            noteTime += (bpms[bpmIndex][0] - lastTick) / (tpb * bpm / 60)
            lastTick = bpms[bpmIndex][0]
            bpm = bpms[bpmIndex][1]
        noteTime += (noteTick - lastTick) / (tpb * bpm / 60)
        if((msg.type == 'note_on') or (msg.type == 'note_off') or (msg.type == 'program_change')):
            sequence.append([tid, noteTime, msg, True, 0])
     

def loadMidi(file):
    global bpms, tpb, mid
    if(type(file) == str):
        mid = mido.MidiFile(file)
    else:
        mid = mido.MidiFile(file=file)
    tpb = mid.ticks_per_beat
    bpms = []
    msgTick = 0
    for msg in mid.tracks[0]:
        msgTick += msg.time
        if(msg.type == 'set_tempo'):
            bpms.append([msgTick, 60000000 / msg.tempo])
    if(len(bpms) == 0):
        log('No tempo found, using 120 as default.')
        bpms = [[0, 120]]
    bpms.append([bpms[-1][0] + 1000000000, 120])

def checkKeyMap():
    global isPlaying, terminating, keyCode, progress, seqLength
    terminating = False
    isPlaying = True
    log('Started checking key map.')
    l = len(keyCode)
    if(l >= 37):
        l = 37
    progress = 0
    seqLength = l
    for i in range(0, l):
        keyDown(0, keyCode[i])
        time.sleep(0.1)
        keyUp(0, keyCode[i])
        if(terminating):
            terminating = False
            break
        progress = i
        time.sleep(0.1)
    progress = l
    log('Checking key map completed.')
    isPlaying = False

def getMetronomePos():
    global ff14WindowHandle, metronomeX, metronomeY
    rect = win32gui.GetWindowRect(ff14WindowHandle[0])
    x = metronomeX + rect[0]
    y = metronomeY + rect[1]
    return x, y

def metronomeEcho():
    global isPlaying, terminating, metronomeColorThreshold, keyCode
    global progress, seqLength
    terminating = False
    isPlaying = True
    log('Started metronome echo.')
    progress = 0
    seqLength = 0
    x, y = getMetronomePos()
    dc = win32gui.GetDC(0)
    within = False
    pressingKey = 0
    keyId = 0
    while(True):
        if(terminating):
            if(pressingKey > 0):
                keyUp(0, pressingKey)
            break
        try:
            green = (win32gui.GetPixel(dc, x, y) >> 8) & 0xff
        except:
            log('Unable to read from metronome at (' + str(x) + ',' + str(y) + ').')
            terminating = True
            continue
        if(green > 128):
            if(not within):
                pressingKey = keyCode[keyId]
                keyDown(0, pressingKey)
                keyId += 1
                if(keyId >= len(keyCode)):
                    keyId = 0
                within = True
        else:
            if(within):
                keyUp(0, pressingKey)
                pressingKey = 0
                within = False
        time.sleep(0.001)
    win32gui.ReleaseDC(0, dc)
    progress = 1
    seqLength = 1
    log('Metronome echo completed.')
    isPlaying = False

def playMidiInputIndividual(index = 0):
    global isPerforming, terminating, ff14WindowHandle, keyCode, sendMidiInput, useMidiDevice
    global differentSpacing, minNoteLength, progress, seqLength
    if(len(ff14WindowHandle) == 0):
        return
    terminating = False
    isPerforming = True
    log('Started playing from midi device input for Game ' + str(index) + '.')
    try:
        if useMidiDevice[index] == '默认':
             mi = mido.open_input()
        else:
            mi = mido.open_input(useMidiDevice[0])
        pressingKey = 0
        while(True):
            if(terminating):
                break
            for msg in mi.iter_pending():
                if((msg.type == 'note_on') and (msg.velocity > 0)):
                    if((msg.note < 48) or (msg.note > 84)):
                        continue
                    key = keyCode[msg.note - 48]
                    if(pressingKey > 0):
                        if(sendMidiInput[index]):
                            keyUp(index, pressingKey)
                        time.sleep(differentSpacing)
                    pressingKey = key
                    if(sendMidiInput[index]):
                        keyDown(index, key)
                    time.sleep(minNoteLength)
                elif((msg.type == 'note_off') or ((msg.type == 'note_off') and (msg.velocity == 0))):
                    if((msg.note < 48) or (msg.note > 84)):
                        continue
                    key = keyCode[msg.note - 48]
                    if(pressingKey == key):
                        if(sendMidiInput[index]):
                            keyUp(index, key)
                        pressingKey = 0
                        time.sleep(differentSpacing)
            time.sleep(0.001)
        mi.close()
    except Exception as e:
        print(e)
        try:
            mi.close()
        except:
            pass
    log('Playing midi device input completed.')
    isPerforming = False


def playMidiInput():
    global isPerforming, terminating, ff14WindowHandle, keyCode, sendMidiInput, useMidiDevice
    global differentSpacing, minNoteLength, progress, seqLength
    if(len(ff14WindowHandle) == 0):
        return
    terminating = False
    isPerforming = True
    log('Started playing from midi device input.')
    try:
        if useMidiDevice[0] == '默认':
             mi = mido.open_input()
        else:
            mi = mido.open_input(useMidiDevice[0])
        pressingKey = 0
        while(True):
            if(terminating):
                break
            for msg in mi.iter_pending():
                if((msg.type == 'note_on') and (msg.velocity > 0)):
                    if((msg.note < 48) or (msg.note > 84)):
                        continue
                    key = keyCode[msg.note - 48]
                    if(pressingKey > 0):
                        if(sendMidiInput[0]):
                            keyUp(0, pressingKey)
                        if(sendMidiInput[1]):
                            keyUp(1, pressingKey)
                        time.sleep(differentSpacing)
                    pressingKey = key
                    if(sendMidiInput[0]):
                        keyDown(0, key)
                    if(sendMidiInput[1]):
                        keyDown(1, key)
                    time.sleep(minNoteLength)
                elif((msg.type == 'note_off') or ((msg.type == 'note_off') and (msg.velocity == 0))):
                    if((msg.note < 48) or (msg.note > 84)):
                        continue
                    key = keyCode[msg.note - 48]
                    if(pressingKey == key):
                        if(sendMidiInput[0]):
                            keyUp(0, key)
                        if(sendMidiInput[1]):
                            keyUp(1, key)
                        pressingKey = 0
                        time.sleep(differentSpacing)
            time.sleep(0.001)
        mi.close()
    except Exception as e:
        print(e)
        try:
            mi.close()
        except:
            pass
    log('Playing midi device input completed.')
    isPerforming = False

def playMidiInputToTwoGames():
    global isPerforming, terminating, ff14WindowHandle, keyCode, sendMidiInput, useMidiDevice
    global differentSpacing, minNoteLength, progress, seqLength
    if(len(ff14WindowHandle) == 0):
        return
    terminating = False
    isPerforming = True
    log('Started splitting midi device input to two game windows.')
    device = useMidiDevice[0]
    try:
        if device == "默认":
            mi = mido.open_input()
        else:
            mi = mido.open_input(device)
        pressingKey = [0, 0]
        while(True):
            if(terminating):
                break
            for msg in mi.iter_pending():
                if((msg.velocity > 0) and (msg.type == 'note_on')):           
                    if((msg.note < 24) or (msg.note > 96)):
                        continue
                    if(msg.note < 60):
                        key = keyCode[msg.note - 24]
                        hid = 0
                    else:
                        key = keyCode[msg.note - 60]
                        hid = 1                        
                    if(pressingKey[hid] > 0):
                        keyUp(hid, pressingKey[hid])
                        time.sleep(differentSpacing)
                    pressingKey[hid] = key
                    keyDown(hid, key)
                    time.sleep(minNoteLength)
                elif((msg.velocity == 0) or (msg.type == 'note_off')):
                    if((msg.note < 24) or (msg.note > 96)):
                        continue
                    if(msg.note < 60):
                        key = keyCode[msg.note - 24]
                        hid = 0
                    else:
                        key = keyCode[msg.note - 60]
                        hid = 1                        
                    if(pressingKey[hid] == key):
                        keyUp(hid, key)
                        pressingKey[hid] = 0
                        time.sleep(differentSpacing)
            time.sleep(0.001)
        mi.close()
    except Exception as e:
        print(e)
        try:
            mi.close()
        except:
            pass
    log('Playing midi device input completed.')
    isPerforming = False

def play(mode=''):
    global mid, sequence, isPlaying, terminating, keyCode, metronomeColorThreshold
    global progress, seqLength, scheduledBeginTime, timeToNextNote

    if(mode == 'time'):
        beginTime = scheduledBeginTime + 1
    else:
        beginTime = time.time() + 1
    progress = 0
    seqLength = 0
    
    _thread.start_new_thread(playMidiInput, ())
    try:
        mo = mido.open_output()
    except Exception as e:
        print(e)
        mo.close()
        return
    
    terminating = False
    isPlaying = True
    sequence = []
    startIndex = 0
    
    for track in mid.tracks:
        startIndex += 2
        processTrack(track, 0, 0)
    sequence = sorted(sequence, key = lambda x: x[1] + int(x[3]) * 0.001)
                   
    log('Sequence contains ' + str(len(sequence)) + ' events.')

    if(mode == 'metronome'):
        log('Waiting for metronome signal.')
        dc = win32gui.GetDC(0)
        x, y = getMetronomePos()
        beatCount = 0
        within = False
        while(True):
            if(terminating):
                if(seqLength > 0):
                    progress = seqLength
                else:
                    progress = 1
                    seqLength = 1
                log('Playing cancelled.')
                isPlaying = False
                return
            try:
                green = (win32gui.GetPixel(dc, x, y) >> 8) & 0xff
            except:
                log('Unable to read from metronome at (' + str(x) + ',' + str(y) + ').')
                terminating = True
                continue
            if(green > 128):
                if(not within):
                    within = True
                    beatCount += 1
                    if(beatCount == 9):
                        beginTime = time.time() + 1
                        break
            else:
                if(within):
                    within = False
            time.sleep(0.001)
        win32gui.ReleaseDC(0, dc)
    elif(mode == 'time'):
        while(True):
            if(terminating):
                if(seqLength > 0):
                    progress = seqLength
                else:
                    progress = 1
                    seqLength = 1
                log('Scheduled playing cancelled.')
                isPlaying = False
                return
            if(time.time() >= beginTime - 1):
                break
            time.sleep(0.01)
    
    seqLength = len(sequence)
    log('Started playing midi file.')

    for i in range(startIndex, len(sequence)):
        progress = i
        while(True):
            ttn = beginTime + sequence[i][1] + delay - time.time()
            if(sequence[i][3]):
                timeToNextNote = ttn
            else:
                timeToNextNote = 0
            if(ttn <= 0):
                break
            time.sleep(0.001)
            if(terminating):
                break
        if(terminating):
            break
        mo.send(sequence[i][2])
        
    timeToNextNote = 1000000
    mo.close()
    if(seqLength > 0):
        progress = seqLength
    else:
        progress = 1
        seqLength = 1
    log('Playing midi file completed.')
    isPlaying = False
    
