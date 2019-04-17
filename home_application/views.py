# -*- coding: utf-8 -*-
import json

from django.http import JsonResponse
from blueking.component.shortcuts import get_client_by_request, logger
from common.mymako import render_mako_context, render_json
from home_application.celery_tasks import async_task
from home_application.models import executeHistory


def home(request):
    """
    首页
    """
    # 获取业务
    client = get_client_by_request(request)
    client.set_bk_api_ver('v2')
    res = client.cc.search_business()
    bk_biz_list = res.get('data').get('info')
    return render_mako_context(request, '/home_application/home.html', {'bk_biz_list': bk_biz_list})


def dev_guide(request):
    """
    开发指引
    """
    return render_mako_context(request, '/home_application/dev_guide.html')


def contactus(request):
    """
    联系我们
    """
    return render_mako_context(request, '/home_application/contact.html')


def history(request):
    """
    历史
    """
    client = get_client_by_request(request)
    client.set_bk_api_ver('v2')
    res = client.cc.search_business()
    bk_biz_list = res.get('data').get('info')
    return render_mako_context(request, '/home_application/history.html',{'bk_biz_list': bk_biz_list})


def search_set(request):
    """
    根据业务查询集群
    :return:
    """
    client = get_client_by_request(request)
    client.set_bk_api_ver('v2')
    bk_token = request.COOKIES.get("bk_token")
    bk_biz_id = request.GET["bizID"]
    param = {
        "bk_token": bk_token,
        "bk_biz_id": bk_biz_id,
        "fields": [
            "bk_set_name",
            "bk_set_id"
        ]
    }
    res = client.cc.search_set(param)
    set_list = res.get('data').get('info')
    return render_mako_context(request, '/home_application/set_table.html', {'set_list': set_list})


def search_host(request):
    """
    根据业务id，集群id获取主机列表信息
    :param request:
    :return:
    """
    client = get_client_by_request(request)
    client.set_bk_api_ver('v2')
    bk_biz_id = request.GET["bizID"]
    bk_set_id = request.GET["setID"]
    param  = {
        "bk_biz_id": bk_biz_id,
        "condition": [
            {
                "bk_obj_id": "set",
                "fields": [
                ],
                "condition": [
                    {
                        "field": "bk_set_id",
                        "operator": "$eq",
                        "value": int(bk_set_id)
                    }
                ]
            }
        ]
    }
    res = client.cc.search_host(param)
    if res.get('result', False):
        bk_host_list = res.get('data').get('info')
    else:
        bk_host_list = []
        logger.error(u"请求主机列表失败：%s" % res.get('message'))
    bk_host_list = [
        {
            'bk_host_name': host['host']['bk_host_name'],
            'bk_host_innerip': host['host']['bk_host_innerip'],
            'bk_cloud_id': host['host']['bk_cloud_id'][0]['bk_inst_id'],
            'bk_cloud_name': host['host']['bk_cloud_id'][0]['bk_inst_name'],
            'bk_os_name': host['host']['bk_os_name']
        }
        for host in bk_host_list
    ]

    return render_mako_context(request, '/home_application/host_table.html', {'bk_host_list': bk_host_list})


def execute_job(request):
    """
    执行作业
    :param request:
    :return:
    """
    print 11111
    # client.set_bk_api_ver('v2')
    username = request.user.username
    # req = json.loads(request.body)
    # host_list = req.get('hosts')
    # biz_id = req.get('bizID')
    # job_id = req.get('jobID')

    host_list = request.GET['hosts']
    biz_id = request.GET["bizID"]
    job_id = request.GET['jobID']
    job_detail_param = {
        "bk_biz_id": biz_id,
        "bk_job_id": job_id
    }
    client = get_client_by_request(request)
    job_detail_result = client.job.get_job_detail(job_detail_param)
    if job_detail_result and job_detail_result.get('result'):
        steps = job_detail_result.get("data").get("steps")
        steps[0]['ip_list'] = list(eval(host_list))
        execute_job_param = {
            "bk_biz_id": biz_id,
            "bk_job_id": job_id,
            "steps": steps
        }
        print execute_job_param
        execute_job_result = client.job.execute_job(execute_job_param)
        if execute_job_result and execute_job_result.get("result"):
            job_instance_id = execute_job_result.get('data').get('job_instance_id')
            async_task.apply_async(args=(job_instance_id, biz_id, username), kwargs={})
            return render_json(
                {
                    "result": True,
                    "message": u"任务开始执行",
                })


def history_list(request):
    biz_id = request.GET['bizID']
    if biz_id == 'all':
        history_result = executeHistory.objects.all()
    else:
        history_result = executeHistory.objects.filter(bizID=biz_id)
    display_list = []
    for history in history_result:
        temp = {
            "createUser": history.createUser,
            "log": history.log,
            "bizName": history.bizName,
            "ipList": history.ipList,
            "actionTime": str(history.actionTime),
            "jobID": history.jobID
        }
        if history.jobStatus == 3:
            temp["jobStatus"] = 'success'
        else:
            temp["jobStatus"] = 'failed'
        display_list.append(temp)
    return render_mako_context(request, '/home_application/history_table.html',
                               {'historyList': display_list})


