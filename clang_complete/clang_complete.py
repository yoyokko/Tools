#!/usr/bin/python

import os
import sys
from subprocess import *
import shutil


def usage():
    print 'Usage: \nclang_complete XcodeProjectFolderPath'
    print 'clang_complete XcodeProjectFolderPath ProjectName TargetName'


def targets_in_projectfile(projectfile):
    """
    find the target list of given xcode project file
    @return: target list
    @rtype : list
    """
    targets = []
    output = Popen(["xcrun", "xcodebuild", "-list", "-project", projectfile], stdout=PIPE).communicate()[0]
    findtargetsection = False
    spacenumber = 0

    for line in output.split('\n'):
        if True == findtargetsection and spacenumber > 0 and line.startswith(' ' * spacenumber * 2):
            targets.append(line.strip())
        elif line.strip() == 'Targets:':
            findtargetsection = True
            spacenumber = len(line) - len(line.strip())
        else:
            findtargetsection = False

    return targets


def get_clang_args(projectfolder, projectfilepath, target):
    """
    find the arguments which xcode used to build source files
    @param projectfilepath:
    @param target:
    @return: argument string
    @rtype: str
    """

    deriveddatapath = os.path.join(projectfolder, '.clang_driveddata')
    if os.path.exists(deriveddatapath):
        shutil.rmtree(deriveddatapath)
    # Popen(['xcrun', 'xcodebuild', 'clean', '-project', projectfilepath, '-target', target], stdout=PIPE).communicate()
    output = Popen(['xcrun', 'xcodebuild', '-configuration', 'Debug', '-project', projectfilepath, '-target', target,
                    "BUILD_DIR=%s" % deriveddatapath,
                    "BUILD_ROOT=%s" % deriveddatapath,
                    "CACHE_ROOT=%s/cache" % deriveddatapath,
                    "OBJROOT=%s" % deriveddatapath,
                    "SHARED_PRECOMPS_DIR=%s/Build/Intermediates/PrecompiledHeaders" % deriveddatapath,
                    "SYMROOT=%s/Build/Products" % deriveddatapath], stdout=PIPE).communicate()[0]

    buildoutput = output.split('\n')
    args = ''
    for idx, line in enumerate(buildoutput):
        if line.startswith('CompileC') and '.m ' in line and idx < (len(buildoutput)-2):
            for idy in range(idx+1, len(buildoutput)):
                nexline = buildoutput[idy]
                if '/usr/bin/clang' in nexline:
                    startstr = '/usr/bin/clang'
                    endstr = '-MMD -MT dependencies'
                    start = nexline.find(startstr)+len(startstr)
                    end = nexline.find(endstr, start)
                    args = nexline[start:end].strip()
                    break
            break
    return args


def get_all_header_folder(projectfolder):
    def directories_contains_source(files):
        for f in files:
            if f.split(".")[-1] in ("h", "m", "mm", "c"):
                return True
        return False
    folderlist = []
    for (path, dirs, files) in os.walk(projectfolder):
        if directories_contains_source(files):
            folderlist.append(path)
    return folderlist


def format_directories(directories):
    return "\n".join(['-I"%s"' % (p,) for p in directories])

def main(argv):
    if len(argv) != 1 and len(argv) != 3:
        usage()
        sys.exit(1)

    projectfolder = os.path.abspath(argv[0])

    if not os.path.exists(projectfolder):
        print '%s is not exists.' % projectfolder
        sys.exit(1)

    projectname = targetname = None

    if len(argv) == 3:
        projectname = argv[1]
        targetname = argv[2]
    else:
        for root, dirs, files in os.walk(projectfolder):
            for dir in dirs:
                if dir.endswith('.xcodeproj'):
                    projectname = dir
                    break

    targets = targets_in_projectfile(os.path.join(projectfolder, projectname))

    if len(targets) == 0:
        print 'The xcode project %s has no valid target.' % projectname
        sys.exit(1)

    if None == targetname:
        targetname = targets[0]
    elif not targetname in targets:
        print 'Target "%s" is not in existing target list %s.' % (targetname, targets)

    print 'Processing target "%s" in project "%s"...' % (targetname, projectname)

    argstring = get_clang_args(projectfolder, os.path.join(projectfolder, projectname), targetname)
    args = (('\n-'.join((' '+argstring).split(' -'))).strip('\n ')).split('\n')
    if len(args) == 0:
        print('Build target "%s" failed. Please check your code.' % targetname)
        sys.exit(1)

    folderlist = get_all_header_folder(projectfolder)

    clang_args = ('\n'.join([x for x in args if '\\ ' not in x])).strip('\n ') + '\n' + format_directories([x for x in folderlist if '\\ ' not in x])

    clang_completefile = os.path.join(projectfolder, '.clang_complete')
    if os.path.exists(clang_completefile):
        os.rename(clang_completefile, clang_completefile+'.bak')
    os.system('echo "%s" > %s' % (clang_args, clang_completefile))

    filteredpath = [x for x in args if '\\ ' in x] + [x for x in folderlist if '\\ ' in x]
    if len(filteredpath) > 0:
        print 'Please make sure there is no white space in your project path and target name because of a bug in clang.\n' \
              'Following paths are not valid, correct the path with "\ " and try again.\n'
        for path in [x for x in filteredpath]:
            print path

    print
    print 'Processed target "%s" in project "%s". Please restart your MacVIM now.' % (targetname, projectname)

if __name__ == "__main__":
    main(sys.argv[1:])
