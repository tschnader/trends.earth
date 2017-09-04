# -*- coding: utf-8 -*-
import os
import glob
import json
import stat
import subprocess
import tinys3
import zipfile

from paver.easy import *
from paver.doctools import html

options(
    plugin = Bunch(
        name = 'LDMP',
        ext_libs = path('LDMP/ext-libs'),
        ext_src = path('LDMP/ext-src'),
        source_dir = path('LDMP'),
        gui_dir = path('LDMP/gui'),
        resource_files = [path('LDMP/resources.qrc')],
        package_dir = path('.'),
        tests = ['test'],
        excludes = [
            '.DS_Store',  # on Mac
            'test-output',
            'data_prep_scripts',
            'ext-src',
            'coverage*',
            'nose*',
            '*.pyc',
        ],
        # skip certain files inadvertently found by exclude pattern globbing
        skip_exclude = []
    )
)

# Handle long filenames or readonly files on windows, see: 
# http://bit.ly/2g58Yxu
def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)  

@task
@cmdopts([
    ('clean', 'c', 'Clean out dependencies first'),
    ('develop', 'd', 'Do not alter source dependency git checkouts'),
])
def setup(options):
    """Install run-time dependencies"""
    clean = getattr(options, 'clean', False)
    develop = getattr(options, 'develop', False)
    ext_libs = options.plugin.ext_libs
    ext_src = options.plugin.ext_src
    if clean:
        rmtree(ext_libs)
    ext_libs.makedirs()
    runtime, test = read_requirements()
    os.environ['PYTHONPATH'] = ext_libs.abspath()
    for req in runtime + test:
        if '#egg' in req:
            urlspec, req = req.split('#egg=')
            localpath = ext_src / req
            if not develop:
                if localpath.exists():
                    cwd = os.getcwd()
                    os.chdir(localpath)
                    print(localpath)
                    sh('git pull')
                    os.chdir(cwd)
                else:
                    sh('git clone  %s %s' % (urlspec, localpath))
            req = localpath

        sh('easy_install -a -d %(ext_libs)s %(dep)s' % {
            'ext_libs' : ext_libs.abspath(),
            'dep' : req
        })


def read_requirements():
    """Return a list of runtime and list of test requirements"""
    lines = path('requirements.txt').lines()
    lines = [ l for l in [ l.strip() for l in lines] if l ]
    divider = '# test requirements'

    try:
        idx = lines.index(divider)
    except ValueError:
        raise BuildFailure(
            'Expected to find "%s" in requirements.txt' % divider)

    not_comments = lambda s,e: [ l for l in lines[s:e] if l[0] != '#']
    return not_comments(0, idx), not_comments(idx+1, None)


def _install(folder, options):
    '''install plugin to qgis'''
    compile_files(options)
    plugin_name = options.plugin.name
    src = path(__file__).dirname() / plugin_name
    dst = path('~').expanduser() / folder / 'python' / 'plugins' / plugin_name
    src = src.abspath()
    dst = dst.abspath()
    if not hasattr(os, 'symlink'):
        rmtree(dst)
        src.copytree(dst)
    elif not dst.exists():
        src.symlink(dst)

@task
def install(options):
    _install(".qgis2", options)

@task
def installdev(options):
    _install(".qgis-dev", options)

@task
def install3(options):
    _install(".qgis3", options)

@task
@cmdopts([
    ('tests', 't', 'Package tests with plugin'),
])
def package(options):
    """Create plugin package"""
    tests = getattr(options, 'tests', False)
    package_file = options.plugin.package_dir / ('%s.zip' % options.plugin.name)
    with zipfile.ZipFile(package_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        if not tests:
            options.plugin.excludes.extend(options.plugin.tests)
        _make_zip(zf, options)
    return package_file


@task
@cmdopts([
    ('tests', 't', 'Package tests with plugin'),
    ('clean', 'c', 'Clean out dependencies first'),
    ('develop', 'd', 'Do not alter source dependency git checkouts'),
])
def deploy(options):
    setup(options)
    package(options)
    with open(os.path.join(os.path.dirname(__file__), 'aws_credentials.json'), 'r') as fin:
        keys = json.load(fin)
    conn = tinys3.Connection(keys['access_key_id'], keys['secret_access_key'])
    f = open('LDMP.zip','rb')
    print('Uploading package to S3')
    conn.upload('Sharing/LDMP.zip', f, 'landdegradation', public=True)
    print('Package uploaded')

@task
def install_devtools():
    """Install development tools"""
    try:
        import pip
    except:
        error('FATAL: Unable to import pip, please install it first!')
        sys.exit(1)

    pip.main(['install', '-r', 'requirements-dev.txt'])


@task
@consume_args
def pep8(args):
    """Check code for PEP8 violations"""
    try:
        import pep8
    except:
        error('pep8 not found! Run "paver install_devtools".')
        sys.exit(1)

    # Errors to ignore
    ignore = ['E203', 'E121', 'E122', 'E123', 'E124', 'E125', 'E126', 'E127',
        'E128', 'E402']
    styleguide = pep8.StyleGuide(ignore=ignore,
                                 exclude=['*/ext-libs/*', '*/ext-src/*'],
                                 repeat=True, max_line_length=79,
                                 parse_argv=args)
    styleguide.input_dir(options.plugin.source_dir)
    info('===== PEP8 SUMMARY =====')
    styleguide.options.report.print_statistics()


@task
@consume_args
def autopep8(args):
    """Format code according to PEP8
    """
    try:
        import autopep8
    except:
        error('autopep8 not found! Run "paver install_devtools".')
        sys.exit(1)

    if any(x not in args for x in ['-i', '--in-place']):
        args.append('-i')

    args.append('--ignore=E261,E265,E402,E501')
    args.insert(0, 'dummy')

    cmd_args = autopep8.parse_args(args)

    excludes = ('ext-lib', 'ext-src')
    for p in options.plugin.source_dir.walk():
        if any(exclude in p for exclude in excludes):
            continue

        if p.fnmatch('*.py'):
            autopep8.fix_file(p, options=cmd_args)


@task
@consume_args
def pylint(args):
    """Check code for errors and coding standard violations"""
    try:
        from pylint import lint
    except:
        error('pylint not found! Run "paver install_devtools".')
        sys.exit(1)

    if not 'rcfile' in args:
        args.append('--rcfile=pylintrc')

    args.append(options.plugin.source_dir)
    lint.Run(args)


def _make_zip(zipFile, options):
    excludes = set(options.plugin.excludes)
    skips = options.plugin.skip_exclude

    src_dir = options.plugin.source_dir
    exclude = lambda p: any([path(p).fnmatch(e) for e in excludes])
    def filter_excludes(root, items):
        if not items:
            return []
        # to prevent descending into dirs, modify the list in place
        for item in list(items):  # copy list or iteration values change
            itempath = path(os.path.relpath(root)) / item
            if exclude(item) and item not in skips:
                debug('Excluding %s' % itempath)
                items.remove(item)
        return items

    for root, dirs, files in os.walk(src_dir):
        for f in filter_excludes(root, files):
            relpath = os.path.relpath(root)
            zipFile.write(path(root) / f, path(relpath) / f)
        filter_excludes(root, dirs)

################################################
# Below is based on pb_tool:
# https://github.com/g-sherman/plugin_build_tool
def check_path(app):
    """ Adapted from StackExchange:
        http://stackoverflow.com/questions/377017
    """

    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    def ext_candidates(fpath):
        yield fpath
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    fpath, fname = os.path.split(app)
    if fpath:
        if is_exe(app):
            return app
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, app)
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate):
                    return candidate

    return None

def file_changed(infile, outfile):
    try:
        infile_s = os.stat(infile)
        outfile_s = os.stat(outfile)
        return infile_s.st_mtime > outfile_s.st_mtime
    except:
        return True

def compile_files(options):
    # Compile all ui and resource files

    # check to see if we have pyuic4
    pyuic4 = check_path('pyuic4')

    if not pyuic4:
        print("pyuic4 is not in your path---unable to compile your ui files")
    else:
        ui_files = glob.glob('{}/*.ui'.format(options.plugin.gui_dir))
        ui_count = 0
        for ui in ui_files:
            if os.path.exists(ui):
                (base, ext) = os.path.splitext(ui)
                output = "{0}.py".format(base)
                if file_changed(ui, output):
                    print("Compiling {0} to {1}".format(ui, output))
                    subprocess.check_call([pyuic4, '-o', output, ui])
                    ui_count += 1
                else:
                    print("Skipping {0} (unchanged)".format(ui))
            else:
                print("{0} does not exist---skipped".format(ui))
        print("Compiled {0} UI files".format(ui_count))

    # check to see if we have pyrcc4
    pyrcc4 = check_path('pyrcc4')

    if not pyrcc4:
        click.secho(
            "pyrcc4 is not in your path---unable to compile your resource file(s)",
            fg='red')
    else:
        res_files = options.plugin.resource_files
        res_count = 0
        for res in res_files:
            if os.path.exists(res):
                (base, ext) = os.path.splitext(res)
                output = "{0}.py".format(base)
                if file_changed(res, output):
                    print("Compiling {0} to {1}".format(res, output))
                    subprocess.check_call([pyrcc4, '-o', output, res])
                    res_count += 1
                else:
                    print("Skipping {0} (unchanged)".format(res))
            else:
                print("{0} does not exist---skipped".format(res))
        print("Compiled {0} resource files".format(res_count))