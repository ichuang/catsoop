'''
Interface to asynchronous grading queue
'''

import os
import time
import uuid
import shutil
import hashlib
from . import cslog
from . import debug_log
from . import base_context

LOGGER = debug_log.LOGGER
#LOGGER.setLevel(1)

#-----------------------------------------------------------------------------

class CatsoopQueueWithFilesystem:
    def __init__(self):
        self.CURRENT = {"queued": [], "running": set()}
        self.cs_data_root = base_context.cs_data_root
        self.checker_db_loc = os.path.join(self.cs_data_root, "_logs", "_checker")
        self.staging = os.path.join(self.checker_db_loc, "staging")
        self.running = os.path.join(self.checker_db_loc, "running")
        self.results = os.path.join(self.checker_db_loc, "results")
        self.queued  = os.path.join(self.checker_db_loc, "queued")
        return

    def enqueue(self, context, job_desc):
        '''
        job_desc: dict describing job to be queued
    
        Return UUID for the job
        '''
        id_ = str(uuid.uuid4())
        loc = os.path.join(self.staging, id_)
        os.makedirs(os.path.dirname(loc), exist_ok=True)
        with open(loc, "wb") as f:
            f.write(context["csm_cslog"].prep(job_desc))
        newloc = os.path.join(
            self.queued,
            "%s_%s" % (time.time(), id_),	# use time as prefix, for queue entry ordering
        )
        os.makedirs(os.path.dirname(newloc), exist_ok=True)				# make 'queued' directory if needed 
        LOGGER.info("[catsoop.queue.enqueue] moving %s to %s" % (loc, newloc))
        shutil.move(loc, newloc)
        return id_
        
    def get_oldest_from_queue(self, context, move_to_running=True):
        '''
        Get the top job from the queue
    
        return None if quene is empty, else return job spec
        '''
        waiting = sorted(os.listdir(self.queued))
        if not waiting:
            return None
        first = waiting[0]
        qfn = os.path.join(self.queued, first)
        with open(qfn, "rb") as f:
            try:
                row = cslog.unprep(f.read())
            except Exception as err:
                LOGGER.error("[checker] failed to read queue log file %s, error=%s, traceback=%s" % 
                             (qfn, err, traceback.format_exc()))
                row = None
    
        if row:
            _, magic = first.split("_")
            row["magic"] = magic
    
        if not os.path.exists(self.running):
            os.makedirs(self.running, exist_ok=True)
    
        if row and move_to_running:
            shutil.move(os.path.join(self.queued, first), os.path.join(self.running, magic))
            LOGGER.debug("Moving from queued to  running: %s " % first)
    
        return row
    
    def get_results(self, id_):
        '''
        Get results from job execution, if available
        '''
        checker_loc = os.path.join(
            self.results,
            id_[0],
            id_[1],
            id_,
        )
        if not os.path.isfile(checker_loc):
            return None
        try:
            with open(checker_loc, "rb") as fp:
                row = cslog.unprep(fp.read())
        except:
            row = None
        return row
    
    def save_results(self, context, id_, data, remove_from_running=True):
        '''
        Save results from async job run
        '''
        magic = id_	        # make temporary file to write results to
        temploc = os.path.join(self.staging, "results.%s" % magic)
        with open(temploc, "wb") as f:
            f.write(cslog.prep(data))
        # move that file to results, close the handle to it.
        newloc = os.path.join(self.results, magic[0], magic[1], magic)
        os.makedirs(os.path.dirname(newloc), exist_ok=True)
        shutil.move(temploc, newloc)
    
        if remove_from_running:
            os.unlink(os.path.join(self.running, id_))
            
    def move_running_back_to_queued(self, context):
        '''
        Move anything running to back of queue
        Called at start of grader.watch_queue_and_run process
        '''
        for f in os.listdir(self.running):
            shutil.move(os.path.join(self.running, f), os.path.join(self.queued, "0_%s" % f))
    
    def store_file_upload(self, context, question_name, data, filename):
        '''
        Upload file content and metadata info
        
        Return name of directory where this was stored
        '''
        if context["csm_cslog"].ENCRYPT_KEY is not None:
            seed = (
                context["cs_path_info"][0]
                if context["cs_path_info"]
                else context["cs_path_info"]
            )
            _path = [
                context["csm_cslog"]._e(i, repr(seed))
                for i in context["cs_path_info"]
            ]
        else:
            _path = context["cs_path_info"]
        dir_ = os.path.join(
            self.cs_data_root, "_logs", "_uploads", *_path
        )
        os.makedirs(dir_, exist_ok=True)
        hstring = hashlib.sha256(data).hexdigest()
        info = {
            "filename": filename,
            "username": context["cs_username"],
            "time": context["csm_time"].detailed_timestamp(
                context["cs_now"]
            ),
            "question": question_name,
            "hash": hstring,
        }
    
        disk_fname = "_csfile.%s%s" % (uuid.uuid4().hex, hstring)
        dirname = os.path.join(dir_, disk_fname)
        os.makedirs(dirname, exist_ok=True)
        with open(os.path.join(dirname, "content"), "wb") as f:
            f.write(context["csm_cslog"].compress_encrypt(data))
        with open(os.path.join(dirname, "info"), "wb") as f:
            f.write(context["csm_cslog"].prep(info))
        return dirname
    

    def clear_all_queues(self, context):
        '''
        Clear waiting queue and all running (used for unit testing, to start from a standard state)
        '''
        for qdir in [self.running, self.queued]:
            if not os.path.exists(qdir):
                continue
            for f in os.listdir(qdir):
                os.unlink(os.path.join(qdir, f))
    
    def update_current_job_status(self):
        '''
        Update local information about status of current jobs.
        Used by reporter.
        '''
        self.CURRENT["queued"] = [i.split("_")[1] for i in sorted(os.listdir(self.queued))]
        self.CURRENT["running"] = {i.name for i in os.scandir(self.running)}
        crun = self.CURRENT["running"]
        if crun:
            LOGGER.debug("[catsoop.queue] updater queued=%s" % crun)
        
    def get_running_job_start_time(self, jobid):
        '''
        Return start time (in floating sec since epoch) of specified job
        '''
        try:
            start = os.stat(os.path.join(self.running, jobid)).st_ctime
        except:
            start = time.time()
        return start

    def get_current_job_status(self, jobid):
        '''
        Return status of specified job, as a string (either "running" or "results")
        or as an int, giving the position in the queue.
        Used by reporter.
        '''
        status = None
        try:
            status = self.CURRENT["queued"].index(jobid) + 1
        except:
            if jobid in self.CURRENT["running"]:
                status = "running"
            elif os.path.isfile(os.path.join(self.results, jobid[0], jobid[1], jobid)):
                status = "results"
        return status
        
    def get_file_upload(self, filename, **kwargs):
        '''
        Get uploaded file
        '''
        raise Excetpion("[catsoop.queue] get_file_upload not implemented!")

    def init_db():
        '''
        Initializae database connection
        '''
        return

#-----------------------------------------------------------------------------

class CatsoopQueueWithFirestore:
    '''
    Queue based on google firestore cloud database
    '''
    COLLECTION = "QUEUE"
    FILE_COLLECTION = "FILE_UPLOADS"

    def __init__(self):
        self.init_db()
        return

    def enqueue(self, context, job_desc):
        '''
        job_desc: dict describing job to be queued
    
        Return UUID for the job
        '''
        id_ = str(uuid.uuid4())
        col = self.COLLECTION + "_waiting"
        ref = self.db.collection(col).document(id_)
        data = {'job': job_desc,
                'time': time.time(),
        }
        ref.set(data)
        return id_
        
    def get_oldest_from_queue(self, context, move_to_running=True):
        '''
        Get the top job from the queue
        return None if quene is empty, else return job spec, and move job to running.
        Do this atomically.
        '''
        wcol = self.COLLECTION + "_waiting"
        wref = self.db.collection(wcol)
        
        rcol = self.COLLECTION + "_running"
        rref = self.db.collection(rcol)

        if not move_to_running:
            docs = list(wref.order_by("time").limit(1).stream())
            if not docs:
                return None
            doc = docs[0]
            data = doc.to_dict()
            job_id = doc.id

        else:        
            @firestore.transactional
            def update_in_transaction(transaction, wref, rref):		# atomic move from waiting to running
                next_to_run = list(wref.order_by("time").limit(1).stream(transaction=transaction))
                if not next_to_run:
                    return None, None
                next_to_run = next_to_run[0]
    
                job_id = next_to_run.id
                data = next_to_run.to_dict()
                transaction.set(rref.document(job_id), data)		# create running job
                transaction.delete(wref.document(job_id))		# delete waiting job
                return job_id, data
                
            transaction = self.db.transaction()
            job_id, data = update_in_transaction(transaction, wref, rref)
            if job_id:
                LOGGER.debug("[catsoop.queue] Moving from queued to running: %s " % job_id)

        if job_id:
            row = data['job']
            row["magic"] = job_id
            LOGGER.debug("[catsoop.queue] get_oldest_from_queue: returning %s" % row)
            return row
        return None
    
    def get_results(self, id_):
        '''
        Get results from job execution, if available
        Return None if not available
        '''
        ccol = self.COLLECTION + "_results"
        ref = self.db.collection(ccol).document(id_)
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict().get("data")
        try:
            row = context["csm_cslog"].unprep(data)
        except Exception as err:
            LOGGER.error("[catsoop.queue] Failed to decode results from job %s, err=%s" % (id_, err))
            row = None
        return row
    
    def save_results(self, context, id_, data):
        '''
        Save results from async job run
        '''
        ccol = self.COLLECTION + "_results"
        rcol = self.COLLECTION + "_running"
        ref = self.db.collection(ccol).document(id_)
        doc = {'data': cslog.prep(data)}
        ref.set(doc)
        LOGGER.debug("[catsoop.queue] saved queue results for %s" % id_)

        ref = self.db.collection(rcol).document(id_)
        ref.delete()
        LOGGER.debug("[catsoop.queue] removed %s from running" % id_)
            
    def move_running_back_to_queued(self, context, expiration=30):
        '''
        Move anything running and "too old", to back of waiting queue
        Called at start of grader.watch_queue_and_run process
        expiration: number of seconds after which a job is "too old"
        '''
        cutoff = time.time() - expiration
        rcol = self.COLLECTION + "_running"
        wcol = self.COLLECTION + "_waiting"

        rref = self.db.collection(rcol)
        query = rref.where("time", "<", cutoff)
        for doc in query.stream():
            dref = rref.document(doc.id)

            @firestore.transactional
            def update_in_transaction(transaction, dref, wref):		# atomic move from running to waiting
                doc = dref.get(transaction=transaction)
                job_id = doc.id
                data = doc.to_dict()
                transaction.set(wref.document(job_jd), data)		# create waiting
                translaction.delete(dref)				# delete running
                return job_id, data
            
            transaction = self.db.transaction()
            job_id, data = update_in_transaction(transaction, dref, wref)
            LOGGER.warning("[catsoop.queue] moved job %s from running to waiting (job creation time=%s)" % (job_id, data.get("time")))

    def clear_all_queues(self, context):
        '''
        Clear waiting queue and all running (used for unit testing, to start from a standard state)
        '''
        rcol = self.COLLECTION + "_running"
        wcol = self.COLLECTION + "_waiting"
        for col in [rcol, wcol]:
            for doc in self.db.collection(col).stream():
                doc.reference.delete()
                LOGGER.warning("[catsoop.queue] deleting %s from %s" % (doc.id, col))

    def store_file_upload(self, context, question_name, data, filename):
        '''
        Upload file content and metadata info
        
        Return name of directory where this was stored
        '''
        col = self.FILE_COLLECTION

        hstring = hashlib.sha256(data).hexdigest()
        disk_fname = "csfile.%s%s" % (uuid.uuid4().hex, hstring)
        ref = self.db.collection(col).document(disk_fname)

        info = {
            "course": context['cs_course'],
            "filename": filename,
            "username": context["cs_username"],
            "time": context["csm_time"].detailed_timestamp(context["cs_now"]),
            "question": question_name,
            "hash": hstring,
            "path": context["cs_path_info"],
        }
        doc = {'info': info,
               'data': data,
        }
        ref.set(doc)
        LOGGER.warning("[catsoop.queue] saved file upload from username=%s to document '%s' (%d bytes)" % (context["cs_username"],
                                                                                                           disk_fname,
                                                                                                           len(data)))
        return disk_fname
    
    def get_file_upload(self, **kwargs):
        '''
        Get uploaded file(s); keyword arguments specify search filter, e.g. question="q000001"
        Return a list of dicts of data, where each dict has {'info': ..., "data": file_data}
        '''
        col = self.FILE_COLLECTION
        ref = self.db.collection(col)
        for key, val in kwargs.items():
            ref = ref.query(key, "==", val)
        doc = ref.stream()
        results = [ x.to_dict() for x in doc ]
        return results
        
    def init_db(self):
        '''
        Initializae database connection
        '''
        self.db = firestore.Client()		# document database

#-----------------------------------------------------------------------------

class CatsoopQueueWithMongoDB:
    '''
    Queue based on mongo DB.

    All jobs are stored in a single collection.  The "status" field is either
    "waiting", "running", or "completed".  Each mongodb action is atomic, and
    this atomicity is used to guarantee that only one worker gets each job.
    '''
    COLLECTION = "QUEUE"
    FILE_COLLECTION = "FILE_UPLOADS"

    def __init__(self):
        self.CURRENT = {"queued": [], "running": set()}
        self.init_db()
        return

    def enqueue(self, context, job_desc):
        '''
        job_desc: dict describing job to be queued
    
        Return UUID for the job
        '''
        id_ = str(uuid.uuid4())
        col = self.db[self.COLLECTION]
        data = {'job': job_desc,
                'time': time.time(),
                'status': 'waiting',
        }
        ref = col.replace_one({"_id": id_}, data, upsert=True)
        return id_
        
    def get_oldest_from_queue(self, context, move_to_running=True):
        '''
        Get the oldest job waiting on the queue (ie oldest, based on mongodb natural ordering)
        return None if quene is empty, else return job spec, and move job to running.
        Do this atomically.

        Add job_data["magic"] = job_id
        Return dict with job data.
        '''
        col = self.db[self.COLLECTION]

        if not move_to_running:
            doc = col.find_one({'status': 'waiting'}, sort=[('$natural', 1)])
            if not doc:
                return None

            job_id = doc.get("_id")
            data = doc

            if not job_id:
                return None
        else:        
            doc = col.find_one_and_update({'status': 'waiting'},
                                          {"$set": {'status': 'running',
                                                    'start': time.time(),
                                          }},
                                          sort=[('$natural', 1)],
            )
            if not doc:
                return None
            job_id = doc.get("_id")
            data = doc
            LOGGER.debug("[catsoop.queue] Moving from queued to running: %s " % job_id)

        row = data['job']
        row["magic"] = job_id
        LOGGER.debug("[catsoop.queue] get_oldest_from_queue: returning %s" % row)
        return row
    
    def get_results(self, id_):
        '''
        Get results from job execution, if available
        Return None if not available
        '''
        col = self.db[self.COLLECTION]

        doc = col.find_one({'_id': id_, 'status': 'completed'})
        if not doc:
            return None
        data = doc.get("results")
        try:
            row = cslog.unprep(data)
        except Exception as err:
            LOGGER.error("[catsoop.queue] Failed to decode results from job %s, err=%s" % (id_, err))
            row = None
        return row
    
    def save_results(self, context, id_, data):
        '''
        Save results from async job run: move status from running to completed
        '''
        col = self.db[self.COLLECTION]
        doc = col.find_one_and_update({"_id": id_,
                                       'status': 'running'},
                                      {"$set": {'status': 'completed',
                                                'end': time.time(),
                                                'results': cslog.prep(data) },
                                      }
        )
        if not doc:
            LOGGER.error("[catsoop.queue.save_results] Tried to save results for %s, but no doc found!" % id_)
            return None
        
        LOGGER.debug("[catsoop.queue] saved queue results for %s and moved from running to completed" % id_)
            
    def move_running_back_to_queued(self, context, expiration=30):
        '''
        Move anything running and "too old", to back of waiting queue
        Called at start of grader.watch_queue_and_run process
        expiration: number of seconds after which a job is "too old"
        '''
        cutoff = time.time() - expiration
        col = self.db[self.COLLECTION]

        cnt = 0
        while True:
            doc = col.find_one_and_update({'status': 'running', 'time': {"$lt": cutoff}},
                                          {"$set": {'status': 'waiting'}},
            )
            if not doc:
                break
            LOGGER.error("[catsoop.queue.move_running_back_to_queue] (%s) Moved %s from running to waiting, time=%s" % (cnt, doc['_id'], doc['time']))
            cnt += 1
            if (cnt > 1000):
                LOGGER.error("[catsoop.queue.move_running_back_to_queue] already moved %s back: aborting" % cnt)
                break
    
    def update_current_job_status(self):
        '''
        Update local information about status of current jobs.
        Used by reporter.
        '''
        col = self.db[self.COLLECTION]

        queued = []
        running = []
        for doc in col.find({'status': 'waiting'}, sort=[('$natural', 1)]):
            queued.append(doc.get("_id"))

        for doc in col.find({'status': 'running'}, sort=[('$natural', 1)]):
            running.append(doc.get("_id"))

        self.CURRENT["queued"] = queued
        self.CURRENT["running"] = running

        
    def get_running_job_start_time(self, jobid):
        '''
        Return start time (in floating sec since epoch) of specified job
        Used by reporter.
        '''
        col = self.db[self.COLLECTION]
        ret = col.find_one({"_id": jobid, 'status': "running"})
        if not ret:
            return None
        return ret.get("start")

    def get_current_job_status(self, jobid):
        '''
        Return status of specified job, as a string (either "running" or "results")
        or as an int, giving the position in the queue.
        Used by reporter.
        '''
        status = None
        col = self.db[self.COLLECTION]
        try:
            status = self.CURRENT["queued"].index(jobid) + 1
        except:
            if jobid in self.CURRENT["running"]:
                status = "running"
            elif col.find_one({"_id": jobid, "status": "completed"}):
                status = "results"
        return status

    def clear_all_queues(self, context):
        '''
        Clear waiting queue and all running (used for unit testing, to start from a standard state)
        '''
        col = self.db[self.COLLECTION]

        ret = col.delete_many({})
        LOGGER.error("[catsoop.queue.clear_all_queues] deleted %s queue jobs" % ret.deleted_count)

    def store_file_upload(self, context, question_name, data, filename):
        '''
        Upload file content and metadata info
        
        Return name of collection where this was stored
        '''
        col = self.db[self.FILE_COLLECTION]

        hstring = hashlib.sha256(data).hexdigest()
        disk_fname = "csfile.%s%s" % (uuid.uuid4().hex, hstring)
        ref = self.db.collection(col).document(disk_fname)

        info = {
            "course": context['cs_course'],
            "filename": filename,
            "username": context["cs_username"],
            "time": context["csm_time"].detailed_timestamp(context["cs_now"]),
            "question": question_name,
            "hash": hstring,
            "path": context["cs_path_info"],
        }
        doc = {'info': info,
               'data': data,
               '_id': disk_fname,
        }
        ret = col.insert_one(doc)
        LOGGER.warning("[catsoop.queue] saved file upload from username=%s to document '%s' (%d bytes)" % (context["cs_username"],
                                                                                                           disk_fname,
                                                                                                           len(data)))
        return disk_fname
    
    def get_file_upload(self, **kwargs):
        '''
        Get uploaded file; keyword arguments specify search filter, e.g. question="q000001"
        Return a list of dicts of data, where each dict has {'info': ..., "data": file_data}
        '''
        col = self.db[self.FILE_COLLECTION]

        doc = col.find_one(kwargs)
        return doc
        
    def init_db(self):
        '''
        Initializae database connection
        '''
        mongourl = os.environ.get("MONGODB", None)
        self.client = pymongo.MongoClient(mongourl)
        self.db = self.client.catsoop

#-----------------------------------------------------------------------------

procs = ['enqueue', 'get_oldest_from_queue', 'get_results', 'save_results',
         'move_running_back_to_queued', 'store_file_upload', 'get_file_upload',
         'get_current_job_status', 'get_running_job_start_time',
         'update_current_job_status',
         'clear_all_queues', 'init_db',
]

USE_CLOUD_DB = os.environ.get("USE_CLOUD_DB")
if USE_CLOUD_DB=="mongodb":
    import pymongo
    QUEUE = CatsoopQueueWithMongoDB()

elif USE_CLOUD_DB:
    from google.cloud import firestore
    QUEUE = CatsoopQueueWithFirestore()

else:
    QUEUE = CatsoopQueueWithFilesystem()

for pname in procs:
    exec("%s = QUEUE.%s" % (pname, pname))
        
