#!/usr/bin/env python
#
# 'build.py' is a top-level config/build command line tool for ESP-AT
#
# Copyright 2020 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# WARNING: we don't check for Python build-time dependencies until
# check_environment() function below. If possible, avoid importing
# any external libraries here - put in external script, or import in
# their specific function instead.

import os
import sys
import subprocess
import json
if sys.platform == 'win32':
    from colorama import init

def ESP_LOGI(x):
    print('\033[32m{}\033[0m'.format(x))

def ESP_LOGE(x):
    print('\033[31m{}\033[0m'.format(x))

def gitee_repo_preprocess():
    print('Redirect IDF url to https://gitee.com/EspressifSystems')
    return 'https://gitee.com/EspressifSystems'

def gitee_repo_postprocess():
    print('IDF is Cloned from https://gitee.com/EspressifSystems')

    ret = subprocess.call('cd esp-idf && git submodule init', shell = True)
    if ret:
        raise Exception('git submodule init failed')
    submodule_lists = \
        subprocess.check_output(['git', 'config', '-f', os.path.join('esp-idf', '.gitmodules'), '--list']).decode(encoding='utf-8')

    for line in submodule_lists.split():
        if line.find('.url=') > 0:
            submodule = line.split('=')
            submodule_name = os.path.basename(submodule[1])
            print('Redirect {} to {}'.format(submodule[0],
                                '/'.join(['https://gitee.com/esp-submodules', submodule_name])))
            subprocess.call('cd esp-idf && git config {} {}'.format(submodule[0],
                                '/'.join(['https://gitee.com/esp-submodules',submodule_name])), shell = True)

    print('Update submodule...')
    ret = subprocess.call('cd esp-idf && git submodule update', shell = True)
    if ret:
        raise Exception('git submodule update failed')

preprocess_url = {
    'https://gitee.com/EspressifSystems/esp-at': {'proprocess': gitee_repo_preprocess,
                                                  'postprocess': gitee_repo_postprocess},
    'https://gitee.com/EspressifSystems/esp-at.git': {'proprocess': gitee_repo_preprocess,
                                                      'postprocess': gitee_repo_postprocess},
    'git@gitee.com:EspressifSystems/esp-at.git': {'proprocess': gitee_repo_preprocess,
                                                   'postprocess': gitee_repo_postprocess},
}

def auto_update_idf(platform_name, module_name):
    config_dir = os.path.join(os.getcwd(), 'module_config', 'module_{}'.format(module_name.lower()))

    if not os.path.exists(config_dir):
        config_dir = os.path.join(os.getcwd(), 'module_config',  'module_{}_default'.format(platform_name.lower()))

    idf_branch = ''
    idf_commit = ''
    idf_url = ''

    with open(os.path.join(config_dir, 'IDF_VERSION')) as f:
        for line in f.readlines():
            line = line.strip()
            index = line.find('branch:')
            if index >= 0:
                if len(idf_branch) > 0:
                    sys.exit('ERROR: idf branch is defined')

                idf_branch = line[index + len('branch:'):]
                continue

            index = line.find('commit:')
            if index >= 0:
                if len(idf_commit) > 0:
                    sys.exit('ERROR: idf commit is defined')

                idf_commit = line[index + len('commit:'):]
                continue

            index = line.find('repository:')
            if index >= 0:
                if len(idf_url) > 0:
                    sys.exit('ERROR: idf repository is defined')

                idf_url = line[index + len('repository:'):]
                continue

    if len(idf_branch) <= 0:
        sys.exit('ERROR: idf branch is not defined')

    if len(idf_commit) <= 0:
        sys.exit('ERROR: idf commit is not defined')

    if len(idf_url) <= 0:
        sys.exit('ERROR: idf url is not defined')

    project_remote_url = subprocess.check_output(['git', 'remote', '-v']).decode(encoding='utf-8')
    project_url = project_remote_url.split()[1]

    if not os.path.exists('esp-idf'):
        # check repo
        if project_url in preprocess_url:
            new_url = preprocess_url[project_url]['proprocess']()
            idf_url = '/'.join([new_url, os.path.basename(idf_url)])

        print('Please wait for the SDK download to finish...')
        ret = subprocess.call('git clone -b {} {} esp-idf'.format(idf_branch, idf_url), shell = True)
        if ret:
            raise Exception('git clone failed')

        if project_url in preprocess_url:
            new_url = preprocess_url[project_url]['postprocess']()

    rev_parse_head = subprocess.check_output('cd esp-idf && git rev-parse HEAD', shell = True).decode(encoding='utf-8').strip()
    if rev_parse_head != idf_commit:
        print('old commit:{}'.format(rev_parse_head))
        print('checkout commit:{}'.format(idf_commit))
        print('Please wait for the update to complete, which will take some time')
        ret = subprocess.call('cd esp-idf && git fetch origin {}'.format(idf_branch), shell = True)
        if ret:
            raise Exception('git fetch failed')
        ret = subprocess.call('cd esp-idf && git merge origin/{} {}'.format(idf_branch, idf_branch), shell = True)
        if ret:
            raise Exception('git merge failed')
        ret = subprocess.call('cd esp-idf && git checkout {}'.format(idf_commit), shell = True)
        if ret:
            raise Exception('git checkout failed')
        ret = subprocess.call('cd esp-idf && git submodule update --init --recursive', shell = True)
        if ret:
            raise Exception('git submodule update failed')
        print('Update completed')

def build_project(platform_name, module_name, silence, build_args):
    if platform_name == 'ESP32':
        idf_target = 'esp32'
    elif platform_name == 'ESP32C3':
        idf_target = 'esp32c3'
    else:
        sys.exit('Platform "{}" is not supported'.format(platform_name))

    tool = os.path.join('esp-idf', 'tools', 'idf.py')
    if sys.platform == 'win32':
        sys_cmd = 'set'
        sys_python_path = sys.executable
    elif sys.platform == 'linux2':
        sys_cmd = 'export'
        sys_python_path = sys.executable
    else:
        sys_cmd = 'export'
        if os.environ.get('IDF_PYTHON_ENV_PATH') is None:
            sys_python_path = 'python'
        else:
            sys_python_path = os.path.join(os.environ.get('IDF_PYTHON_ENV_PATH'), 'bin', 'python')

    cmd = '{0} ESP_AT_PROJECT_PLATFORM=PLATFORM_{1} && {0} ESP_AT_MODULE_NAME={2} && {0} ESP_AT_PROJECT_PATH={3} && \
       {0} SILENCE={4} && {5} {6} -DIDF_TARGET={7} {8}'.format(sys_cmd, platform_name, module_name, os.getcwd(), silence, sys_python_path, tool, idf_target, build_args)
    ret = subprocess.call(cmd, shell = True)
    if ret:
        raise Exception('idf.py build failed')
    
    with open(os.path.join('build', 'flash_project_args'), 'r') as rd_f:
        with open(os.path.join('build', 'download.config'), 'w') as wr_f:
            data = rd_f.read().splitlines()
            wr_f.write(' '.join(data))

def get_param_data_info(source_file, sheet_name):
    import xlrd
    import csv
    filename, filetype = os.path.splitext(source_file)
    if filetype == '.csv':
        with open(source_file) as f:
            csv_data = csv.reader(f)
            param_data_list = list(csv_data)

    else:
        print('The file type is not supported.')
        exit()

    return param_data_list


def get_platform_and_module_lists():
    platform_lists = {}
    data_lists = get_param_data_info(
        os.path.join('components', 'customized_partitions', 'raw_data', 'factory_param', 'factory_param_data.csv'), 'Param_Data')

    headers = data_lists[0]

    nrows = len(data_lists)
    ncols = len(data_lists[0])
    platform_index = ncols
    module_name_index = ncols
    description_index = ncols
    for i in range(ncols):  # get platform index
        if headers[i] == 'platform':
            platform_index = i
            break

    for i in range(ncols):  # get module name index
        if headers[i] == 'module_name':
            module_name_index = i
            break

    for i in range(ncols):  # get description index
        if headers[i] == 'description':
            description_index = i
            break

    if platform_index == ncols:
        sys.exit('ERROR: Not found platform in header.')

    if module_name_index == ncols:
        sys.exit('ERROR: Not found module name in header.')

    if description_index == ncols:
        sys.exit('ERROR: Not found description in header.')

    for row in range(1, nrows):  # skip header
        data_list = data_lists[row]
        modules = []

        platform_name = data_list[platform_index].upper()
        module_name = data_list[module_name_index].upper()
        module_info = {'module_name': module_name, 'description': data_list[description_index]}
        if platform_name in platform_lists:
            platform_lists.fromkeys(platform_name, platform_lists[platform_name].append(module_info))
        else:
            platform_lists[platform_name] = [module_info]

    return platform_lists


def choose_project_config():
    info = {}
    info_lists = get_platform_and_module_lists()
    platform_lists = list(info_lists.keys())
    module_info_file = os.path.join('build', 'module_info.json')
    if os.path.exists(module_info_file):
        with open(module_info_file, 'r') as f:
            info = json.load(f)
            if not 'platform' in info or not 'module' in info or not 'silence' in info:
                sys.exit('"{}" configuration error, please delete and reconfigure it'.format(module_info_file))
            platform_name = info['platform']
            module_name = info['module']
           
            if not platform_name in info_lists:
                sys.exit('"{}" configuration error, please delete and reconfigure it'.format(module_info_file))

            # get module_info
            found = False
            for index, module in enumerate(info_lists[platform_name]):
                if module_name == module['module_name']:
                    found = True
                    break

            if not found:
                sys.exit('"{}" configuration error, please delete and reconfigure it'.format(module_info_file))

            if info['silence'] != 0 and info['silence'] != 1:
                sys.exit('"{}" configuration error, please delete and reconfigure it'.format(module_info_file))

            return platform_name.replace('PLATFORM_', ''), module_name, info['silence']

    print('Platform name:')
    for i, platform in enumerate(platform_lists):
        print('{}. {}'.format(i + 1, platform))

    try:
        platform_index = raw_input('choose(range[1,{}]):'.format(i + 1))
    except NameError:
        platform_index = input('choose(range[1,{}]):'.format(i + 1))

    if (not platform_index.isdigit()) or (int(platform_index) - 1 > i):
        sys.exit('Invalid index')

    print('\r\nModule name:')
    platform_name = platform_lists[int(platform_index) - 1]
    info['platform'] = platform_name

    for i, module in enumerate(info_lists[platform_name]):
        if len(module['description']) > 0:
            print('{}. {} (description: {})'.format(i + 1, module['module_name'], module['description']))
        else:
            print('{}. {}'.format(i + 1, module['module_name']))
    try:
        module_index = raw_input('choose(range[1,{}]):'.format(i + 1))
    except NameError:
        module_index = input('choose(range[1,{}]):'.format(i + 1))

    if (not module_index.isdigit()) or (int(module_index) - 1 > i):
        sys.exit('Invalid index')

    module_name = info_lists[platform_name][int(module_index) - 1]['module_name']
    module = info_lists[platform_name][int(module_index) - 1]
    info['module'] = module_name
    info['description'] = module['description']

    print('\r\nEnable silence mode to remove some logs and reduce the firmware size?')
    print('0. No')
    print('1. Yes')
    try:
        silence_index = raw_input('choose(range[0,1]):')
    except NameError:
        silence_index = input('choose(range[0,1]):')

    if not silence_index.isdigit():
        sys.exit('Invalid index')

    if int(silence_index) == 0:
        info['silence'] = 0
    elif int(silence_index) == 1:
        info['silence'] = 1
    else:
        sys.exit('Invalid index')

    res = json.dumps(info)
    if not os.path.exists('build'):
        os.mkdir('build')

    with open(module_info_file, 'w+') as f:
        f.write(res)

    if os.path.exists('sdkconfig'):
        os.remove('sdkconfig')

    return platform_name.replace('PLATFORM_', ''), module_name, info['silence']

def setup_env_variables():
    ESP_LOGI('Ready to set up environment variables..')
    # set IDF_PATH
    idf_path=os.path.join(os.getcwd(), 'esp-idf')
    os.environ['IDF_PATH']=idf_path

    # get ESP-IDF toolchain path and virtual python path
    print('PATH is {}'.format(os.environ.get('PATH')))
    print('IDF_PYTHON_ENV_PATH is {}'.format(os.environ.get('IDF_PYTHON_ENV_PATH')))
    print('sys.platform is {}'.format(sys.platform))

    export_str = ''
    if sys.platform != 'win32' and sys.platform != 'linux2':
        cmd = '{} {} export --format=key-value'.format(sys.executable, os.path.join('esp-idf', 'tools', 'idf_tools.py'))
        try:
            export_str = subprocess.check_output(cmd, shell=True).decode('utf-8')
        except Exception as e:
            print('Not found the environment installed by "install" command, and using the default system environment')

    if export_str:
        # extract toolchain PATH and IDF_PYTHON_ENV_PATH
        idf_tc_env_path = ''
        idf_python_env_path = ''
        for line in export_str.splitlines():
            if line.startswith('PATH='):
                idf_tc_env_path = line.split('PATH=')[1]
            if line.startswith('IDF_PYTHON_ENV_PATH='):
                idf_python_env_path = line.split('IDF_PYTHON_ENV_PATH=')[1]
        # set PATH and IDF_PYTHON_ENV_PATH and print
        at_env_path = os.environ.get('PATH') + ':' + idf_tc_env_path
        os.environ['PATH']=at_env_path
        os.environ['IDF_PYTHON_ENV_PATH']=idf_python_env_path

    print('PATH is {}'.format(os.environ.get('PATH')))
    print('IDF_PYTHON_ENV_PATH is {}'.format(os.environ.get('IDF_PYTHON_ENV_PATH')))

def install_compilation_env():
    # set up ESP-IDF tools
    ESP_LOGI('Ready to set up ESP-IDF tools..')
    cmd = '{} {} install-python-env'.format(sys.executable, os.path.join('esp-idf', 'tools', 'idf_tools.py'))
    ret = subprocess.call(cmd, shell = True)
    if ret:
        raise Exception('set up ESP-IDF python-env failed')
    cmd = '{} {} install'.format(sys.executable, os.path.join('esp-idf', 'tools', 'idf_tools.py'))
    ret = subprocess.call(cmd, shell = True)
    if ret:
        raise Exception('set up ESP-IDF toolchains failed')

    # set up environment variables
    setup_env_variables()

    # install ESP-AT python packages
    ESP_LOGI('Ready to install ESP-AT python packages..')
    if sys.platform == 'win32':
        py_env_path = sys.executable
    else:
        py_env_path = os.path.join(os.environ.get('IDF_PYTHON_ENV_PATH'), 'bin', 'python')
    cmd = '{} -m pip install -r requirements.txt'.format(py_env_path)
    ret = subprocess.call(cmd, shell = True)
    if ret:
        raise Exception('install ESP-AT python packages failed!')

    print('\r\nAll done! You can now run:\r\n\r\n  {}build.py build\r\n'.format('python ' if sys.platform == 'win32' else './'))

def install_prerequisites():
    # install ESP-IDF prerequisites
    ESP_LOGI('Ready to install ESP-IDF prerequisites..')
    cmd = ''
    if sys.platform == 'linux':
        cmd = 'sudo apt-get install git wget flex bison gperf python3 python3-pip python3-setuptools cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0'
    elif sys.platform == 'darwin':
        cmd = 'sudo easy_install pip && brew install cmake ninja dfu-util ccache python3'
    elif sys.platform == 'win32':
        print('Windows Installer Download has already installed all prerequisites.')
    elif sys.platform == 'linux2':
        print('GitLab CI has already installed all prerequisites.')
    else:
        raise Exception('unsupported platform: {} till now.'.format(sys.platform))
    ret = subprocess.call(cmd, shell = True)
    if ret:
        raise Exception('install prerequisites failed! Please manually run:\r\n{}'.format(cmd))

    # install ESP-AT prerequisites
    ESP_LOGI('Ready to install ESP-AT prerequisites..')
    cmd = '{} -m pip install -r requirements.txt'.format(sys.executable)
    ret = subprocess.call(cmd, shell = True)
    if ret:
        raise Exception('install ESP-AT prerequisites failed!')

"""
TODOs:
  1. optimise ESP-IDF clone and version update workflow
  2. optimise ESP-AT and ESP-IDF tools/packages install workflow
  3. remove workaround for windows
"""
def main():
    if sys.platform == 'win32':
        init(autoreset=True)
    argv = sys.argv[1:]

    # install prerequisites
    if (len(argv) == 1 and sys.argv[1] == 'install'):
        install_prerequisites()

    platform_name, module_name, silence = choose_project_config()
    ESP_LOGI('Platform name:{}\tModule name:{}\tSilence:{}'.format(platform_name, module_name, silence))
    build_args = ' '.join(argv)

    auto_update_idf(platform_name, module_name)

    if (len(argv) == 1 and sys.argv[1] == 'install'):
        # install tools and packages only after esp-idf cloned
        install_compilation_env()
        sys.exit(0)

    setup_env_variables()

    build_project(platform_name, module_name, silence, build_args)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        ESP_LOGE('A fatal error occurred: {}'.format(e))
        sys.exit(2)
