# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
import logging
# third-party

# sjva 공용
from framework import db, scheduler
from framework.job import Job
from framework.util import Util

# 패키지
from .plugin import package_name, logger
import system
from .model import ModelSetting


#########################################################
import requests
import urllib
import time
import threading
from datetime import datetime

class Logic(object):
    # 디폴트 세팅값
    """
    db_default = { 
        'auto_start' : 'False',
        'interval' : '20'
    }
    """
    db_default = {
        'auto_start' : 'False',
        'synoindex_server_url' : 'http://172.17.0.1:32699/synoindex',
        'startswith_path' : '',
        'test_filename' : ''
    }


    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            # DB 초기화 
            Logic.db_init()

            # 편의를 위해 json 파일 생성
            from plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))

            # 자동시작 옵션이 있으면 보통 여기서 
            if ModelSetting.query.filter_by(key='auto_start').first().value == 'True':
                Logic.scheduler_start()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def scheduler_start():
        try:
            logger.debug('%s scheduler_start', package_name)
            #interval = ModelSetting.query.filter_by(key='interval').first().value
            # 이 플러그인은 주기적인 스케쥴링 필요없으나 첫 화면 스케쥴러에 표시하기 위해 스케쥴 이용
            interval = 9999
            job = Job(package_name, package_name, interval, Logic.scheduler_function, u"Synoindex", False)
            scheduler.add_job_instance(job)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def scheduler_stop():
        try:
            logger.debug('%s scheduler_stop', package_name)
            scheduler.remove_job(package_name)
            import ktv
            ktv.Logic.remove_listener(Logic.listener)
            import gdrive_scan
            gdrive_scan.Logic.remove_listener(Logic.listener)
            Logic.flag_thread_run = False
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                logger.debug('Key:%s Value:%s', key, value)
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def get_setting_value(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def scheduler_function():
        try:
            logger.debug('%s scheduler_function', package_name)
            import ktv
            ktv.Logic.add_listener(Logic.listener)
            import gdrive_scan
            gdrive_scan.Logic.add_listener(Logic.listener)

            Logic.thread_function()
            #Logic.thread = threading.Thread(target=Logic.thread_function, args=())
            #Logic.thread.daemon = True
            #ogic.thread.start()

            #scheduler.remove_job(package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    # 기본 구조 End
    ##################################################################

    index_wait_list = []
    index_command_list = []
    thread = None
    flag_thread_run = True
    file_check_interval = 60

    @staticmethod
    def server_test(req):
        try:
            url = req.form['url']
            filename = req.form['filename']
            url = '%s?args=-R' % (url)
            if filename.strip() != '':
                url += '&args=%s' % filename
            data = requests.get(url).content
            ret = {'ret':'success', 'log':data}
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret = {'ret':'fail', 'log':str(e)}
        return ret

    @staticmethod
    def get_send_dirname(filename):
        try:
            if not os.path.exists(filename):
                return None
            if os.path.isfile(filename):
                return os.path.dirname(filename)
            else:
                return filename
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        
    @staticmethod
    def listener(*args, **kargs):
        #logger.debug(args)
        logger.debug(kargs)
        try:
            synoindex_server_url = Logic.get_setting_value('synoindex_server_url')
            if kargs['plugin'] == 'ktv':
                #if kargs['type'] == 'add':
                pass
            elif kargs['plugin'] == 'gdrive_scan':
                logger.debug(kargs['filepath'])
                if kargs['filepath'].find('@eaDir') != -1:
                    return
                if kargs['is_file'] == False:
                    return
            kargs['created_time'] =  datetime.now().strftime('%m-%d %H:%M:%S')
            if Logic.is_include_startswith_path(kargs['filepath']):
                Logic.append_wait_list(kargs)
            else:
                logger.debug('not include startswith_path!!')
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def thread_function():
        try:
            while Logic.flag_thread_run:
                try:
                    for _ in range(Logic.file_check_interval):
                        if Logic.flag_thread_run == False:
                            return
                        #logger.debug('.... %s' % _)
                        time.sleep(1)
                    logger.debug('START.. check file')

                    for entity in Logic.index_wait_list:
                        logger.debug(entity)
                        flag_send = False
                        if entity['type'].startswith('add'):
                            if os.path.exists(entity['filepath']):
                                command = '-a' if entity['is_file'] else '-A'
                                flag_send = True
                        else:
                            if not os.path.exists(entity['filepath']):
                                command = '-d' if entity['is_file'] else '-D'
                                flag_send = True
                        if flag_send:
                            Logic.send_command(command, entity['filepath'])
                            Logic.index_wait_list.remove(entity)
                            entity['command'] = command
                            entity['command_time'] =  datetime.now().strftime('%m-%d %H:%M:%S')
                            Logic.index_command_list.append(entity)
                            break
                except Exception as e: 
                    logger.error('Exception:%s', e)
                    logger.error(traceback.format_exc())                
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def send_command(command, filepath):
        try:
            synoindex_server_url = Logic.get_setting_value('synoindex_server_url')
            url = '%s?args=%s&args=%s' % (synoindex_server_url, command, filepath)
            data = requests.get(url).content
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def append_wait_list(data):
        try:
            exist = False
            for item in Logic.index_wait_list:
                if item['filepath'] == data['filepath']:
                    exist = True
            if not exist:
                Logic.index_wait_list.append(data)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def is_include_startswith_path(filepath):
        try:
            startswith_path = Logic.get_setting_value('startswith_path').strip()
            if startswith_path == '':
                return True
            else:
                tmps = startswith_path.split('\n')
                for x in tmps:
                    if filepath.find(x.strip()) != -1:
                        return True
            return False
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
                    
    