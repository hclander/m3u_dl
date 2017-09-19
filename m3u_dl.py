#!/usr/bin/python3

import os
import sys
import requests
import asyncio
from threading import Thread
from queue import Queue
import time
import random
import math
import re
import argparse
from urllib.parse import urlparse
from urllib.parse import urljoin
import tty
import termios



TEST_URL='http://a3live-lh.akamaihd.net/i/antena3_1@35248/index_4_av-p.m3u8'

TEST_FOUT='py_out.ts'

q = Queue()

# Some global vars

_target_duration = 10

args = None

def getch():
    """quick & dirty getchar()"""

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def generator(x=0, delay=1):
    print('Generator {} start'.format(x))
    n = 1
    while True:
        q.put(n)
        print('Generator {}: Input {}'.format(x,n))
        n += 1
        time.sleep(random.uniform(0.0, delay))
        #c time.sleep(delay)

    # print('Generator {} end', x)


def worker(x=0, delay=1):
    print('Worker {} start'.format(x))
    while not q.empty():
        print('Worker {:d}: Element {:d}'.format(x, q.get()))
        time.sleep(random.uniform(0.0, delay))
        q.task_done()

    print('Worker {} done'.format(x))


def wait_for_queue(queue, timeout, delay=1):
    """Espera un tiempo hasta que haya elementos en una queue"""

    total = 0.0
    while queue.empty() and total < timeout:
        total += delay
        time.sleep(delay)

    return not (queue.empty() and total < timeout)


def m3u_url_producer_analyze(url, queue, delay):
    last = ''
    t = 0

    matcher = re.compile('#EXT-X-TARGETDURATION:(\d+)')

    while True:  # FIXME Establecer una condicion de salida
        print('Producer: Refreshing urls from ', url)
        r = requests.get(url)
        if r.status_code == 200:
            # lines = r.text.split('\n')

            lines = [l for l in r.text.split('\n') if l and l[0] != '#' and l > last]

            if lines:

                print('Producer: Retrieved {} new urls in {} s.'.format(len(lines), t*delay))

                for l in lines:
                    # if l and l[0] != '#' and l > last:
                    # if l > last:
                    queue.put(l)
                    last = l
                    # print('Producer: ', l)
                t = 0

        time.sleep(delay)  # Wait for the next refresh
        t += 1


def m3u_url_producer(url, queue, delay):

    last = ''
    while True:  # FIXME Establecer una condicion de salida
        # print('Producer: Refreshing urls from ', url)
        r = requests.get(url)
        if r.status_code == 200:
            # lines = r.text.split('\n')
            lines = [l for l in r.text.split('\n') if l and l[0] != '#' and l > last]

            if lines:

                print('Producer: Retrieved {} new urls'.format(len(lines)))

                for l in lines:
                    # if l and l[0] != '#' and l > last:
                    # if l > last:
                    u = urlparse(l)
                    if u.netloc:
                        queue.put(l)
                    else:
                        queue.put(urljoin(url, l))
                    last = l
                    # print('Producer: ', l)
                print('Producer: {} urls in queue'.format(queue.qsize()))

        time.sleep(delay)   # Wait for the next refresh


def m3u_url_producer_2(url, queue, delay):

    global _target_duration
    last = ''
    mm = re.compile('#EXT-X-TARGETDURATION:(\d+)')

    while True:  # FIXME Establecer una condicion de salida
        # print('Producer: Refreshing urls from ', url)
        r = requests.get(url)
        if r.status_code == 200:
            # lines = r.text.split('\n')
            m = mm.search(r.text)
            _target_duration = int(m.group(1)) if m else 10

            # lines = [l for l in r.text.split('\n') if l and l[0] != '#' and l > last]
            lines = [l for l in r.text.splitlines() if l and l[0] != '#' and l > last]

            # num_sequences = len(lines) if queue.qsize() == 0 else 1

            if lines:

                print('Producer: Retrieved {} new urls'.format(len(lines)))

                for l in lines:
                    # if l and l[0] != '#' and l > last:
                    # if l > last:
                    u = urlparse(l)
                    if u.netloc:
                        queue.put(l)
                    else:
                        queue.put(urljoin(url, l))
                    last = l
                    # print('Producer: ', l)
                print('Producer: {} urls in queue'.format(queue.qsize()))

        if delay < 0:
            auto_delay = _target_duration * queue.qsize() / 2;
            print("Producer: Auto delay: ", auto_delay)
            time.sleep(auto_delay)
        else:
            time.sleep(delay)   # Wait for the next refresh


def timer():
    # return math.floor(time.clock() * 1000000)
    return math.floor(time.time() * 1000000)


def timer_millis():
    return math.floor(time.time() * 1000)
    # return math.floor(time.clock() * 1000)


def m3u_url_worker(f_out, queue, delay):

    print('Url Worker start')

    print('Url Worker: waiting for queue')
    if wait_for_queue(queue, 10):

        # some stats
        n = 0
        total_bytes = 0
        total_time = 0
        qsize = queue.qsize()

        with open(f_out, 'wb') as fo:
            while not queue.empty():
                url = queue.get()
                # print('Url Worker: Processing ', url)
                t0 = timer_millis()
                t1 = t0
                # retries = 3
                # status = 0
                #
                # print("Working with:", url)
                # while retries > 0 and status != 200:
                data = requests.get(url)
                    # retries -= 1
                    # status = data.status_code
                    # if status != 200:
                    #     print("Retrying...")
                    #     time.sleep(1)

                if data.status_code == 200:
                    n += 1
                    fo.write(data.content)
                    t1 = timer_millis()
                    total_bytes += len(data.content)
                    total_time += t1 - t0
                    # print('Url Worker: Retrieve and Wrote {} bytes ({} ms.)'.format(len(data.content), t1-t0))
                    print('Url Worker: Segment {} {} bytes (total {} bytes)  {} ms. (total time {} s.)'.format(n, len(
                        data.content), total_bytes, t1 - t0, total_time / 1000))

                else:
                    print('Url Worker: Error #{} retrieving data '.format(data.status_code), url)

                queue.task_done()

                if delay < 0:
                    time.sleep(_target_duration - (t1 - t0) / 1000)
                else:
                    time.sleep(delay - (t1 - t0) / 1000)  # FIXME buscar otra forma de ajustar lor request
    else:
        print('Url Worker: Queue timeout')

    print('Url Worker stop')


def m3u_url_worker_analyze(f_out, queue, delay):
    print('Url Worker start')

    print('Url Worker: waiting for queue')
    if wait_for_queue(queue, 10):

        # some stats
        n = 0
        total_bytes = 0
        total_time = 0
        qsize = queue.qsize()

        # with open(f_out,'wb') as fo:
        while not queue.empty():
            url = queue.get()
            # print('Url Worker: Processing ', url)
            t0 = timer_millis()
            data = requests.get(url)
            if data.status_code == 200:
                n += 1
                # fo.write(data.content)
                t1 = timer_millis()
                total_bytes += len(data.content)
                # print('Url Worker: Retrieve and Wrote {} bytes ({} ms.)'.format(len(data.content), t1-t0))
                print('Url Worker: Segment {} {} bytes (total {} bytes)  {} ms. (total time {} s.)'.format(n,len(data.content), total_bytes, t1-t0, total_time / 1000))
                total_time += t1-t0
                # if not n % qsize:
                #     print('Url Worker: {} segments ({} bytes) in {} s. ({} ms.)'.format(n, total_bytes, total_time/1000, total_time))
            else:
                print('Url Worker: Error retrieving data')

            queue.task_done()
            time.sleep(delay - (t1 - t0) / 1000)  # FIXME buscar otra forma de ajustar lor request
    else:
        print('Url Worker: Queue timeout')

    print('Url Worker stop')


def test_m3u_url(url, f_out):

    r = requests.get(url)

    if r.status_code == 200:
        lines = [l for l in r.text.split('\n') if l and l[0] != '#']

        if lines:
            # print('Founded {:d} sequences'.format(len(lines)))

            with open(f_out, 'wb') as fo:

                for l in lines:
                    #if l and l[0] != '#':
                    print(l)
                    data = requests.get(l)
                    if data.status_code == 200:
                        fo.write(data.content)
                    else:
                        print("Secuence not found")

def test_gen_work():
    g = Thread(target=generator, args=(0, 1))
    g.setDaemon(True)
    g.start()

    w = Thread(target=worker, args=(0, 1))
    w.setDaemon(True)

    time.sleep(random.randint(3, 10))  # Delay for give time to acumulate values in queue
    w.start()
    q.join()  # wait for all items of the queue being processed
    sys.exit()


def test_m3u_url_prod_work():

    #p = Thread(target=m3u_url_producer_2, args=(TEST_URL, q, 28 * 10 / 2))  # 10 * 28 / 4
    p = Thread(target=m3u_url_producer_2, args=(args.url, q, args.pd))  # 10 * 28 / 4
    p.setDaemon(True)
    p.start()

    w = Thread(target=m3u_url_worker, args=(args.out, q, args.wd))
    #w = Thread(target=m3u_url_worker, args=(TEST_FOUT, q, worker_delay))
    # w = Thread(target=m3u_url_worker_analyze, args=(TEST_FOUT, q, 10))
    w.setDaemon(True)
    w.start()

    wait_for_queue(q, 10)

    q.join()  # Wait queue job done

    # while True:
    #     pass
    # getch()

    print('Exit here!!')


def test_m3u_rul_analysis():

    p = Thread(target=m3u_url_producer_analyze, args=(TEST_URL, q, 5))
    # p.setDaemon(True)
    p.start()


def main():
    global args
    parser = argparse.ArgumentParser(description="m3u download")
    parser.add_argument("-u", "--url", dest="url", help="Input file", required=True)
    parser.add_argument("-o", "--out", dest="out", help="Output file", required=True)
    parser.add_argument("-d", "--worker-delay", dest="wd", type=float, default="-1")
    parser.add_argument("-D", "--producer-delay", dest="pd", type=float, default="-1")
    args = parser.parse_args()

    # test_m3u_rul_analysis()

    # wd = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10

    test_m3u_url_prod_work()

    # test_gen_work()

    # test_m3u_url(TEST_URL,TEST_FOUT)


if __name__=='__main__':
    main()