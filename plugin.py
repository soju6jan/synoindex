# -*- coding: utf-8 -*-
#########################################################
# 고정영역
#########################################################
# python
import os
import sys
import traceback

# third-party
from flask import Blueprint, request, Response, render_template, redirect, jsonify
from flask_login import login_required

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler
from framework.util import Util
from system.logic import SystemLogic
            
# 패키지
package_name = __name__.split('.')[0]
logger = get_logger(package_name)
from logic import Logic
from model import ModelSetting


blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()

plugin_info = {
    'version' : '0.1.0.2',
    'name' : 'Synoindex',
    'category_name' : 'tool',
    'icon' : '',
    'developer' : 'soju6jan',
    'description' : 'Synology 전용 플러그인으로 Synology VideoStation 인식할 수 있도록 자동 인덱싱을 해주는 플러그인이다.<br> - 국내TV 파일처리 : 로컬파일 파일 처리시 자동 인덱싱<br> -  GDrive Scan : 구글 드라이브 변경사항을 감지하여, 파일 추가 삭제시 자동 인덱싱',
    'home' : 'https://github.com/soju6jan/synoindex',
    'more' : 'https://soju6jan.com/archives/1041',
}
#########################################################

# 메뉴 구성.
menu = {
    'main' : [package_name, 'Synoindex'],
    'sub' : [
        ['setting', '설정'], ['wait_list', '대기 목록'], ['command_list', '명령 완료 목록'], ['log', '로그']
    ], 
    'category' : 'tool',
}  

#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/setting' % package_name)

@blueprint.route('/<sub>')
@login_required
def detail(sub): 
    if sub == 'setting':
        setting_list = db.session.query(ModelSetting).all()
        arg = Util.db_list_to_dict(setting_list)
        arg['scheduler'] = str(scheduler.is_include(package_name))
        arg['is_running'] = str(scheduler.is_running(package_name))
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'wait_list':
        arg = {}
        arg['list_type'] = "wait_list"
        return render_template('%s_list.html' % (package_name), arg=arg)
    elif sub == 'command_list':
        arg = {}
        arg['list_type'] = "command_list"
        return render_template('%s_list.html' % (package_name), arg=arg)
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI (보통 웹에서 요청하는 정보에 대한 결과를 리턴한다.)
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    logger.debug('AJAX %s %s', package_name, sub)
    if sub == 'setting_save':
        try:
            ret = Logic.setting_save(request)
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'scheduler':
        try:
            go = request.form['scheduler']
            logger.debug('scheduler :%s', go)
            if go == 'true':
                Logic.scheduler_start()
            else:
                Logic.scheduler_stop()
            return jsonify(go)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return jsonify('fail')
    elif sub == 'server_test':
        try:
            ret = Logic.server_test(request)
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'get_list':
        try:
            list_type = request.form['list_type']
            logger.debug(list_type)
            if list_type == 'wait_list':
                ret = Logic.index_wait_list
            else:
                ret = Logic.index_command_list
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            
    """
    elif sub == 'filelist':
        try:
            ret = Logic.filelist(request)
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'one_execute':
        try:
            ret = Logic.one_execute()
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return jsonify('fail')
    elif sub == 'reset_db':
        try:
            ret = Logic.reset_db()
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    """
    
