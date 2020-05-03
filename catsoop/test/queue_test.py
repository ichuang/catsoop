'''
Test asynchronous grading queue, including qeueing of jobs, and running of checker jobs.

To run just this test:

python setup.py test -s catsoop.test.queue_test.Test_Queue 
'''

import sys
import json
import logging
import catsoop

from catsoop import cslog
from catsoop import grader
from catsoop import csqueue
from catsoop import dispatch

import catsoop.loader as loader
import catsoop.base_context as base_context

from catsoop.test import CATSOOPTest

LOGGER = logging.getLogger("cs")

# uncomment the following to debug
LOGGER.disabled = False
LOGGER.setLevel(0)

# -----------------------------------------------------------------------------

class Test_Queue(CATSOOPTest):
    """
    asynchronous grading test
    """

    def setUp(self):
        CATSOOPTest.setUp(self)
        context = {}
        loader.load_global_data(context)
        assert "cs_unit_test_course" in context
        self.cname = context["cs_unit_test_course"]
        context["csq_python_interpreter"] = "/usr/local/bin/python"
        self.context = context
        # uncomment the following to debug
        LOGGER.setLevel(0)

    def get_logged_in_user(self, context):
        # print("get_logged_in_user context=", context)
        return {'username': 'test_user',
                'role': 'Student',
        }

    def test_question_submit(self):
        '''
        Test submission to an asynchronousely graded problem,
        and the graing of that problem via the queue.
        The checker is explicitly called after submission.
        '''
        print("-----------------------------------------------------------------------------")
        print("Starting test_question_submit test")
        csqueue.clear_all_queues(self.context)
        dispatch.auth.get_logged_in_user = self.get_logged_in_user
        api_token = '123'
        the_path = "/%s/questions" % self.cname
        qid = "q000005"
        form_data = {'action': 'submit',
                     'names': json.dumps([qid]),
                     'api_token': api_token,
                     'data': json.dumps({"q000005":"[1,2,3,4]"}),
        }
        env = {"PATH_INFO": the_path,
               'REMOTE_ADDR': 'dummy_ip',
        }

        status, retinfo, msg = dispatch.main(env, form_data=form_data)

        # print("msg=", msg)
        try:
            ret = json.loads(msg)
        except Exception as err:
            print("Failed to parse result, err=%s" % str(err))
            raise

        qret = ret[qid]
        print("qret=%s" % qret)
        assert "error_msg " not in qret
        assert 'message' in qret

        # get queued entry and run checker on it
        job = csqueue.get_oldest_from_queue(self.context)
        print("job=%s" % job)
        assert 'path' in job
        assert 'username' in job
        assert job['names']
        assert job['action']=='submit'
        assert job is not None

        id_ = job['magic']
        print("Job-id=%s" % id_)
        grader.do_check(job)

        # check for result
        result = csqueue.get_results(id_)
        print("result=%s" % json.dumps(result, indent=4))
        assert result 

        assert 'All of the numbers must be in the range' in result['response']
        assert result['score']==0.0
        
        # check problemstate log
        logpath = (job["username"], job["path"], "problemstate")
        print("logpath=", logpath)
        data = cslog.most_recent(*logpath, {}, lock=False)

        print("problemstate=", data)
        assert data
        assert "timestamp" in data
        assert "last_submit_time" in data
        assert data['checker_ids'][qid]==id_

    def test_question_submit_and_watch_queue(self):
        '''
        Test submission to an asynchronousely graded problem,
        and the graing of that problem via the queue.

        The checker is called by the same queue watching procedure
        which normally runs in the non-stop checker process.
        '''
        print("-----------------------------------------------------------------------------")
        print("Starting watch_queue test")
        csqueue.clear_all_queues(self.context)
        dispatch.auth.get_logged_in_user = self.get_logged_in_user
        api_token = '123'
        the_path = "/%s/questions" % self.cname
        qid = "q000005"
        form_data = {'action': 'submit',
                     'names': json.dumps([qid]),
                     'api_token': api_token,
                     'data': json.dumps({"q000005":"[1,2,3,4]"}),
        }
        env = {"PATH_INFO": the_path,
               'REMOTE_ADDR': 'dummy_ip',
        }

        status, retinfo, msg = dispatch.main(env, form_data=form_data)

        # print("msg=", msg)
        try:
            ret = json.loads(msg)
        except Exception as err:
            print("Failed to parse result, err=%s" % str(err))
            raise

        qret = ret[qid]
        # print("qret=%s" % qret)
        assert "error_msg " not in qret
        assert 'message' in qret

        # get queued entry and run checker on it
        job = csqueue.get_oldest_from_queue(self.context, move_to_running=False)
        print("job=%s" % job)
        assert 'path' in job
        assert 'username' in job
        assert job['names']
        assert job['action']=='submit'
        assert job is not None

        id_ = job['magic']
        print("Job-id=%s" % id_)

        csqueue.update_current_job_status()
        status = csqueue.get_current_job_status(id_)
        print("status=", status)
        assert status==1

        grader.watch_queue_and_run(max_finished=1)

        csqueue.update_current_job_status()
        status = csqueue.get_current_job_status(id_)
        print("status=", status)
        assert status=="results"

        # check for result
        result = csqueue.get_results(id_)
        print("result=%s" % json.dumps(result, indent=4))
        assert result 

        assert 'All of the numbers must be in the range' in result['response']
        assert result['score']==0.0
        
        # check problemstate log
        logpath = (job["username"], job["path"], "problemstate")
        print("logpath=", logpath)
        data = cslog.most_recent(*logpath, {}, lock=False)

        print("problemstate=", data)
        assert data
        assert "timestamp" in data
        assert "last_submit_time" in data
        assert data['checker_ids'][qid]==id_
