#!/usr/bin/python
import json
import sys
import requests

#------------------------------------------------------------
# Simple demo of the (asynchronous) external grading interface,
#   and uploaded file access
#
# Xqueue API consists of:
#    0) login:          Log in
#    1) get_queuelen:   Get length of specific queue
#    2) get_submission: Get single submission from a specific queue
#    3) put_result:     Return the results of a submission
#------------------------------------------------------------
def main():
    #xqueue_url = 'http://xqueue.edx.org/'
    xqueue_url = 'http://ec2-50-17-47-60.compute-1.amazonaws.com/'
    if len(sys.argv) > 1:
        queue_name = sys.argv[1]
    else:
        queue_name = 'null'

    # 0. Log in
    #------------------------------------------------------------
    s = requests.session()
    r = s.post(xqueue_url+'xqueue/login/', data={'username':'kimth','password':'password'})
    (error, msg) = parse_xreply(r.text)
    if error: # We'll assume no error code for the remainder of the demo
        print msg
        return

    # 1. Get length of queue
    #------------------------------------------------------------
    r = s.get(xqueue_url+'xqueue/get_queuelen/', params={'queue_name':queue_name})
    (_, queuelen) = parse_xreply(r.text)
    print "Queue '%s' has %d awaiting jobs" % (queue_name, int(queuelen))
    if queuelen < 1:
        return

    # 2. Contact xqueue and get a student submission
    #------------------------------------------------------------
    r = s.get(xqueue_url+'xqueue/get_submission/', params={'queue_name':queue_name})
    (_, xpackage) = parse_xreply(r.text)

    # Deserialize the package
    xpackage = json.loads(xpackage)

    xheader = xpackage['xqueue_header'] # Xqueue callback, secret key
    xbody   = xpackage['xqueue_body']   # Grader-specific serial data
    xfiles  = xpackage['xqueue_files']  # JSON-serialized Dict {'filename': 'uploaded_file_url'} of student-uploaded files

    xfiles_dict = json.loads(xfiles)
    if xfiles_dict: # Check for any uploaded files
        uploaded_file_url = xfiles_dict.values()[0] # Expecting just one file for 6.00x "pyxserver"
        r = requests.get(uploaded_file_url)
        uploaded_submission = r.text
        
        # Surgery of payload for pyxserver, which is still not really expecting a file...
        xbody = json.loads(xbody)
        xbody.pop('student_response')
        xbody.update({'student_response': uploaded_submission})
        xbody = json.dumps(xbody)

    # The current 'pull_once' routine is a wrapper for the synchronous 6.00x grader (pyxserver)
    #   So, pyxserver should be running in the background...
    payload = {'xqueue_body': xbody, 'xqueue_files': xfiles}
    r = requests.post('http://127.0.0.1:3031',data=json.dumps(payload))
    grader_reply = r.text # Serialized text

    # 3. Return graded result to xqueue
    #------------------------------------------------------------
    returnpackage = {'xqueue_header': xheader,
                     'xqueue_body'  : grader_reply,}
    r = s.post(xqueue_url+'xqueue/put_result/', data=returnpackage)


def parse_xreply(xreply_str):
    try:
        xreply = json.loads(xreply_str)
        return_code = xreply['return_code'] # Nonzero return code indicates error
        msg = xreply['content']
    except Exception:
        return (1, 'Unexpected reply from server.')
    return (return_code, msg)


if __name__ == "__main__":
    main()
