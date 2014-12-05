'''
Documentation, License etc.

@package module
'''

import subprocess
import tempfile
import shutil
import urllib2
import sys
import os
import json
import urlparse
import httplib
import zipfile
import platform

tempPath = ''
scriptVersion = 1
basePath = '../../'
basePath = os.path.abspath(basePath)
rsaKey = os.path.join(basePath, 'System/ssh/id_rsa')
aptOfflineExec = sys.executable + ' ' + os.path.join(basePath, 'System/update/apt-offline/apt-offline')
gitHubUrl = 'https://raw.githubusercontent.com/thecooltool/Sandy-Box-Updater/master/'
sshExec = ''
scpExec = ''


def init():
    global sshExec
    global scpExec
    system = platform.system()
    if system == 'Windows':
        sshExec = os.path.join(basePath, 'Windows\Utils\Xming\plink.exe') + ' -pw machinekit -ssh -2 -X machinekit@192.168.7.2'
        scpExec = os.path.join(basePath, 'Windows\Utils\Xming\pscp.exe') + ' -pw machinekit'
    else:
        sshExec = 'ssh -i ' + rsaKey + ' -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null machinekit@192.168.7.2' 
        scpExec = 'scp -i ' + rsaKey + ' -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null' 

    
def info(message):
    sys.stdout.write(message)
    sys.stdout.flush()


def createTempPath():
    global tempPath
    tempPath = tempfile.mkdtemp(prefix='sandy-box-updater')


def clearTempPath():
    shutil.rmtree(tempPath)
    

def exitScript(message):
    sys.stderr.write(message)
    sys.stderr.write('\n')
    
    if tempPath is not '':
        clearTempPath()
    
    sys.exit(1)


def formatSize(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


# Recursively follow redirects until there isn't a location header
def resolveHttpRedirect(url, depth=0):
    if depth > 10:
        raise Exception("Redirected "+depth+" times, giving up.")
    o = urlparse.urlparse(url,allow_fragments=True)
    conn = httplib.HTTPConnection(o.netloc)
    path = o.path
    if o.query:
        path +='?'+o.query
    conn.request("HEAD", path)
    res = conn.getresponse()
    headers = dict(res.getheaders())
    if headers.has_key('location') and headers['location'] != url:
        return resolveHttpRedirect(headers['location'], depth+1)
    else:
        return url
    
    
def downloadFile(url, filePath):
    url = resolveHttpRedirect(url)
    while True:
        request = urllib2.Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0') # Spoof request to prevent caching
        request.add_header('Pragma', 'no-cache')
        u = urllib2.build_opener().open(request)
        meta = u.info()
        contentLength = meta.getheader('content-length')
        if contentLength is not None:   # loop until request is valid
            break
    fileSize = int(contentLength)
    fileSizeStr = formatSize(fileSize)
    print("Downloading: {0}".format(os.path.basename(filePath)))

    f = open(filePath, 'wb')
    fileSizeDl = 0
    blockSize = 8192
    while True:
        buffer = u.read(blockSize)
        if not buffer:
            break

        fileSizeDl += len(buffer)
        fileSizeDlStr = formatSize(fileSizeDl)
        f.write(buffer)
        p = float(fileSizeDl) / fileSize
        status = r"{0}/{1}  [{2:.3%}]".format(fileSizeDlStr, fileSizeStr, p)
        status = status + chr(8)*(len(status)+1)
        info(status)

    info('\n')
    f.close()


def updateScript():
    createTempPath()
    
    remoteFile = gitHubUrl + 'version.txt'
    localFile = os.path.join(tempPath, 'version.txt')
    currentScript = os.path.realpath(__file__)
    scriptName = os.path.basename(currentScript)
    remoteScript = gitHubUrl + scriptName
    localScript = os.path.join(tempPath, scriptName)

    downloadFile(remoteFile, localFile)

    remoteVersion = 0
    with open(localFile, 'r') as f:
        remoteVersion = int(f.readline())

    updated = False
    if remoteVersion > scriptVersion:
        print('Updating update script')
        downloadFile(remoteScript, localScript)
        shutil.copyfile(localScript, currentScript)
        update = True
    
    clearTempPath()
    return updated

def runSshCommand(command):
    lines = ''
    fullCommand = sshExec.split(' ')
    fullCommand.append(command)
    
    p = subprocess.Popen(fullCommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
      retcode = p.poll() #returns None while subprocess is running
      lines += p.stdout.readline()
      if(retcode is not None):
        break
    
    return lines

def testSshConnection():
    info('Testing ssh connection ... ')
    output = runSshCommand('echo testssh')
    if 'testssh' in output:
        info('ok\n')
    else:
        info('failed\n')
        info('Please check your Sandy-Box is properly connected to the computer.\n')
        info('Make sure all drivers are installed and networking is working.\n')
        sys.exit(1)

def copyToHost(localFile, remoteFile):
    lines = ''
    fullCommand = scpExec.split(' ')
    fullCommand.append(localFile)
    fullCommand.append('machinekit@192.168.7.2:' + remoteFile)
    
    info("Copying " + os.path.basename(localFile) + " to remote host ...")
    p = subprocess.Popen(fullCommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
        retcode = p.poll() #returns None while subprocess is running
        line = p.stdout.readline()
        if 'If you trust this host, enter "y" to add the key to' in line:
            p.stdin.write('y\n')    # accept
        if(retcode is not None):
            break
    
    info(" done\n")
    return retcode

def copyFromHost(remoteFile, localFile):
    lines = ''
    fullCommand = scpExec.split(' ')
    fullCommand.append('machinekit@192.168.7.2:' + remoteFile)
    fullCommand.append(localFile)
    
    info("Copying " + os.path.basename(localFile) + " from remote host ...")
    p = subprocess.Popen(fullCommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin = subprocess.PIPE)
    while(True):
        retcode = p.poll() #returns None while subprocess is running
        line = p.stdout.readline()
        if 'If you trust this host, enter "y" to add the key to' in line:
            p.stdin.write('y\n')	# accept
        if(retcode is not None):
            break
    
    info(" done\n")
    return retcode


def checkHostPath(remotePath):
    output = runSshCommand('ls ' + remotePath + ' || echo doesnotexist')
    return not ('doesnotexist' in output)


def removeHostPath(remotePath):
    output = runSshCommand('rm -r -f ' + remotePath + ' || echo removefailed')
    return not ('removefailed' in output)


def moveHostPath(src, dst):
    output = runSshCommand('mv ' + src + ' ' + dst + ' || echo removefailed')
    return not ('removefailed' in output)


def makeHostPath(remotePath):
    output = runSshCommand('mkdir -p ' + remotePath + ' || echo mkdirfailed')
    return not ('mkdirfailed' in output)


def unzipOnHost(zipFile, remotePath):
    info('unzipping ' + os.path.basename(remotePath) + ' ... ')
    output = runSshCommand('unzip ' + zipFile + ' -d ' + remotePath + ' || echo unzipfailed')
    if 'unzipfailed' in output:
        info(' failed\n')
        return False
    else:
        info(' done\n')
        return True


def checkPackage(name):
    info('checking for package ' + name + ' ... ')
    output = runSshCommand('source /etc/profile; dpkg-query -l ' + name + ' || echo not_installed')
    if 'not_installed' in output:
        info('not installed\n')
        return False
    else:
        info('installed\n')
        return True


def installPackage(package, name):
    remotePackage = gitHubUrl + 'packages/' + package
    localPackage = os.path.join(tempPath, package)
    hostPackage = '/tmp/' + package
    
    if not checkPackage(name):
        downloadFile(remotePackage, localPackage)
        copyToHost(localPackage, hostPackage)
        info('Intalling package ' + package + ' ... ')
        output = runSshCommand('source /etc/profile; sudo dpkg -i ' + hostPackage + ' || echo installerror')
        if 'installerror' in output:
            exitScript('installing package ' + package + ' failed')
        info('done\n')


def aptOfflineBase(command):
    sigName = 'apt-offline.sig'
    localSig = os.path.join(tempPath, sigName)
    hostSig = '/tmp/' + sigName
    bundleName = 'bundle.zip'
    localBundle = os.path.join(tempPath, bundleName)
    hostBundle = '/tmp/' + bundleName
    
    info('updating repositories ...')
    output = runSshCommand('sudo apt-offline set ' + command + ' ' + hostSig + ' || echo updateerror')
    if 'updateerror' in output:
        exitScript(' failed')
    else:
        info(' done\n')
    
    if copyFromHost(hostSig, localSig) != 0:
        exitScript('copy failed')
        
    if os.path.isfile(localBundle):
        os.remove(localBundle)
        
    command = aptOfflineExec + ' get --threads 4 --bundle ' + localBundle + ' ' + localSig
    command = command.split(' ')
    info('local update ...')
    p = subprocess.Popen(command)
    while(True):
      retcode = p.poll() #returns None while subprocess is running
      if(retcode is not None):
        break
    
    if retcode != 0:
        exitScript(' failed\n')
    else:
        info(' done\n')
        
    if copyToHost(localBundle, hostBundle) != 0:
        exitScript('copy failed')
        
    info('installing repository update ... ')
    output = runSshCommand('sudo apt-offline install ' + hostBundle + ' || echo installerror')
    if 'installerror' in output:
        exitScript(' failed')
    else:
        info(' done\n')


def aptOfflineUpdate():
    aptOfflineBase('--update --upgrade')
    info('upgrading packages ... ')
    output = runSshCommand('sudo apt-get upgrade -y || echo installerror')
    if 'installerror' in output:
        exitScript(' failed\n')
    else:
        info(' done\n')
        
def aptOfflineInstallPackages(names):
    namesList = names.split(' ')
    necessary = False
    for name in namesList:
        if not checkPackage(name):
            necessary = True
            break
        
    if not necessary:
        return 
    
    aptOfflineBase('--install-packages ' + names + ' --update')
    info('installing packages ... ')
    output = runSshCommand('sudo apt-get install -y ' + names + ' || echo installerror')
    if 'installerror' in output:
        exitScript(' failed\n')
    else:
        info(' done\n')
    
    
def getGitRepoSha(user, repo):
    url = 'https://api.github.com/repos/' + user + '/' + repo + '/git/refs/heads/master'
    
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0') # Spoof request to prevent caching
    request.add_header('Pragma', 'no-cache')
    u = urllib2.build_opener().open(request)
    
    data = '' 
    blockSize = 8192
    while True:
        buffer = u.read(blockSize)
        if not buffer:
            break
        
        data += buffer
        
    repoObject = json.loads(data)
    return repoObject['object']['sha']


def compareHostGitRepo(user, repo, path):
    remoteSha = getGitRepoSha(user, repo)
    
    done = True
    output = runSshCommand('cd ' + path + ';git rev-parse HEAD || echo parseerror')
    if 'parseerror' in output:
        done = False
        
    if not done:    # remote is not git repo, try to read sha file
        shaFile = path + '/git-sha'  # os path join would fail on Windows
        output = runSshCommand('cat ' + shaFile + ' || echo parseerror')
        if 'parseerror' in output:
            return False
        
    hostSha = output.split('\n')[-2]   # sha is on the semi-last line
    
    return remoteSha == hostSha

def compareLocalGitRepo(user, repo, path):
    remoteSha = getGitRepoSha(user, repo)
    
    shaFile = os.path.join(path, 'git-sha')
    if os.path.exists(shaFile):
        with open(shaFile) as f:
            localSha = f.read().split('\n')[-1] # last line in sha file
            f.close()
            
        return remoteSha == localSha
    else:
        return False
    

def downloadGitRepo(user, repo, path):
    url = 'https://github.com/' + user + '/' + repo + '/zipball/master'
    downloadFile(url, path)

def updateHostGitRepo(user, repo, path, commands):
    necessary = False
    fileName = repo + '.zip'
    localFile = os.path.join(tempPath, fileName)
    hostFile = '/tmp/' + fileName
    shaFile = path + '/git-sha'
    tmpPath = path + '-tmp'
    
    info('checking if git repo ' + repo + ' is up to date ... ')
    if not checkHostPath(path):
        necessary = True
        
    if not necessary:
        necessary = not compareHostGitRepo(user, repo, path)
        
    if necessary:
        info('not\n')
        
        downloadGitRepo(user, repo, localFile)
        
        if copyToHost(localFile, hostFile) != 0:
            exitScript('copy failed')
            
        if not removeHostPath(path):
            exitScript('removing path failed')
            
        if not removeHostPath(tmpPath):
            exitScript('removing tmp path failed')
        
        if not unzipOnHost(hostFile, tmpPath):
            exitScript('unzip failed')
            
        if not moveHostPath(tmpPath + '/' + user + '-' + repo + '-*', path):
            exitScript('move failed')
            
        if not removeHostPath(tmpPath):
            exitScript('remove failed')
            
        output = runSshCommand('unzip -z ' + hostFile + ' >> ' + shaFile  + ' || echo commanderror')
        if 'commanderror' in output:
            exitScript('sha dump failed')
            
        for command in commands:
            if command == '':
                continue
            info('executing ' + command + ' ... ')
            output = runSshCommand('source /etc/profile; cd ' + path + '; ' + command + ' || echo commanderror')
            if 'commanderror' in output:
                exitScript(' failed')
            else:
                info(' done\n')
    else:
        info('yes\n')
        
        
def updateLocalGitRepo(user, repo, path):
    necessary = False
    fileName = repo + '.zip'
    localFile = os.path.join(tempPath, fileName)
    shaFile = os.path.join(path, 'git-sha')
    tmpPath = os.path.join(tempPath, repo)
    
    
    info('checking if git repo ' + repo + ' is up to date ... ')
    if not os.path.exists(path):
        necessary = True
        
    if not necessary:
        necessary = not compareLocalGitRepo(user, repo, path)
        
    if necessary:
        info('not\n')
        
        downloadGitRepo(user, repo, localFile)
        
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)
            
        if os.path.exists(tmpPath):
            shutil.rmtree(tmpPath)
        
        info('Extracting zip file  ... ')
        zipComment = ''
        with zipfile.ZipFile(localFile, 'r') as zip:
            zip.extractall(tmpPath)
            zipComment = zip.comment
            zip.close()
        info('done\n')
        
        info('Moving files ... ')
        repoDir = ''
        for item in os.listdir(tmpPath):
            repoDir = os.path.join(tmpPath, item)
            if os.path.isdir(repoDir):
                break
        for item in os.listdir(repoDir):
            itemPath = os.path.join(repoDir, item)
            targetPath = os.path.join(path, item)
            shutil.move(itemPath, targetPath)
        shutil.rmtree(tmpPath)
        info('done\n')
        
        info('Writing sha file ... ')
        with open(shaFile, 'w') as f:
            f.write(zipComment)
            f.close()
        info('done\n')
    else:
        info('yes\n')

    
def updateFat(dirName, zipCode, shaCode):
    necessary = False
    localShaFile = os.path.join(tempPath, dirName + '.sha')
    localZipFile = os.path.join(tempPath, dirName + '.zip')
    zipShaFile = os.path.join(basePath, 'System/update/sha/' + dirName + '.sha')
    remoteZipUrl = 'https://wolke.effet.info/public.php?service=files&t=' + zipCode + '&download'
    remoteShaUrl = 'https://wolke.effet.info/public.php?service=files&t=' + shaCode + '&download'
            
    # check local sha
    info('checking if ' + dirName + ' on FAT partition is up to date ... ')
    downloadFile(remoteShaUrl, localShaFile)
    with open(localShaFile) as f:
        remoteSha = f.read()
        f.close()
        
    if os.path.exists(zipShaFile):
        with open(zipShaFile) as f:
            localSha = f.read()
            f.close()
        
        if localSha != remoteSha:
            necessary = True
    else:
        necessary = True
    
    if necessary:
        info('not\n')
        
        downloadFile(remoteZipUrl, localZipFile)
        
        zipTmpPath = os.path.join(tempPath, 'fat')
        info('Extracting zip file  ... ')
        if os.path.exists(zipTmpPath):
            shutil.rmtree(zipTmpPath)
        with zipfile.ZipFile(localZipFile, 'r') as zip:
            zip.extractall(tempPath)
            zip.close()
        info('done\n')
        
        info('Moving files ... ')
        for item in os.listdir(zipTmpPath):
            itemPath = os.path.join(zipTmpPath, item)
            targetPath = os.path.join(basePath, item)
            if os.path.exists(targetPath):
                if os.path.isdir(targetPath):
                    shutil.rmtree(targetPath)
                else:
                    os.remove(targetPath)
            shutil.move(itemPath, targetPath)
        shutil.rmtree(zipTmpPath)
        info('done\n')
        
        info('Copying sha file ... ')
        shutil.copyfile(localShaFile, zipShaFile)
        info('done\n')
    else:
        info('yes\n')

    
def proceedMessage():
    info('This script will update the Sandy-Box system.\n')
    info('The update script will download a lot of data.\n')
    while True:
        info('Do you want to proceed? (y/n): ')
        proceed = sys.stdin.readline().strip()
        if proceed == 'n':
            sys.exit(1)
            return
        elif proceed == 'y':
            break
        else:
            info('wrong input, please try again\n')
    

def checkWindowsProcesses(execs):
    cmd = 'WMIC PROCESS get Commandline'
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for line in proc.stdout:
        for entry in execs:
            execPath = os.path.join(basePath, entry[1])
            if execPath in line:
                info('Please close ' + entry[0] + ' before updating\n')
                sys.exit(1)
                return

def main():
    init()
    
    if platform.system() == 'Windows':  # check open applications
        execs = [['Notepad++', 'Window\\Utils\\Notepad++\\notepad++.exe'],
                ['WinSCPPortable', 'Windows\\Utils\\WinSCPPortable\\WinSCPPortable++.exe'],
                ['Putty', 'Windows\\Utils\\Xming\\PAGEANT.EXE'],
                ['Putty', 'Windows\\Utils\\Xming\\plink.exe'],
                ['Putty', 'Windows\\Utils\\Xming\\PSCP.EXE'],
                ['Putty', 'Windows\\Utils\\Xming\\PSFTP.EXE'],
                ['Putty', 'Windows\\Utils\\Xming\\putty.exe'],
                ['Putty', 'Windows\\Utils\\Xming\\PUTTYGEN.EXE'],
                ['Xming', 'Windows\\Utils\\Xming\\xkbcomp.exe'],
                ['Xming', 'Windows\\Utils\\Xming\\Xming.exe']]
        checkWindowsProcesses(execs)
    testSshConnection()
    createTempPath()
    
    updateFat('Windows', '54ae29d8d0420dfd78d7a2466fa09a40', '1657018afa545b87e2b5d51863d60b34')
    updateFat('Linux', '3426231688a24d36d9d18e94f8a8c9ff', 'ed0ee4b645a706048bab687129bf3967')
    updateFat('Mac', '2eea41e315b930a1dd5a700221b6f280', '14bd0a2f48dc4f7f72755956bdf5a6cc')
    updateFat('Doc', '7aaf5ae4aa1194a1d7e5c481824bdae3', 'e22919092f76ba8a87fce4ed885376df')
    updateFat('Other', '5d484f1887937e22ceada1bb916e863d', '0f44627c04c56a7e55e590268a21329b')
    
    if not makeHostPath('~/nc_files/share'):
        exitScript('failed to create directory')
    
    installPackage('apt-offline_1.2_all.deb', 'apt-offline')
    aptOfflineUpdate()
    aptOfflineInstallPackages('machinekit-dev zip unzip')
    
    updateHostGitRepo('strahlex', 'AP-Hotspot', '~/bin/AP-Hotspot', ['sudo make install'])
    updateHostGitRepo('strahlex', 'Cetus', '~/Cetus', [''])
    updateHostGitRepo('strahlex', 'Machineface', '~/Machineface', [''])
    #updateHostGitRepo('strahlex', 'mjpeg-streamer', '~/bin/mjpeg-streamer', [])
    updateHostGitRepo('thecooltool', 'machinekit-configs', '~/machinekit-configs', [])
    updateHostGitRepo('thecooltool', 'example-gcode', '~/nc_files/examples', [])
    updateLocalGitRepo('thecooltool', 'example-gcode', os.path.join(basePath, 'nc_files/examples'))
    
    clearTempPath()
