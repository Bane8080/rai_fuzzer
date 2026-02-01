import requests
from threading import Thread
import queue
from tqdm import tqdm
import time
import threading 
from colorama import init, Fore, Style
from art import text2art
import argparse
import sys
import datetime

init(autoreset=True)
print(Fore.MAGENTA + text2art('RAI_FUZZER'))
def fuzz(url, progress, queue_lock,timeout):
    date=str(datetime.datetime.today())
    file_name = 'report' + '_' + date[:10] + '_' + date[11:19]

    error_count=0
    error_request_count=0
    while True:
        # Безопасное получение из очереди
        with queue_lock:
            if lines_queue.empty():
                break
            lines_fuzz = lines_queue.get()
        
        full_url = url + lines_fuzz
        
        try:
            response = requests.get(
                full_url, 
                timeout=timeout,  # tаймаут для безопасности
                allow_redirects=False  # не следуем редиректам при фаззинге
            )
        
            # Выводим только интересные статусы
            with open(file_name,'a+') as file:
                if response.status_code == 200:
                    progress.write(Fore.GREEN + f"[OK {response.status_code}] {full_url}")
                    file.write(f"[OK {response.status_code}] : {full_url}"+'\n')
                elif response.status_code == 301:
                    progress.write(Fore.CYAN + f"[REDIRECT {response.status_code}] {full_url}")
                    file.write(f"[REDIRECT {response.status_code}] : {full_url}"+'\n')
                elif response.status_code == 401 or response.status_code == 403:
                    progress.write(Fore.MAGENTA + f"[Unauthorized /Forbidden {response.status_code}] {full_url}")
                    file.write(f"[Unauthorized /Forbidden {response.status_code}] : {full_url}"+'\n')
                elif response.status_code == 500:
                    progress.write(Fore.RED + f"Internal Server Error [{response.status_code}] {full_url}")
                    file.write(f"[Internal Server Error {response.status_code}] : {full_url}"+'\n')

        except requests.RequestException as e:
            error_request_count+=1
            progress.write(Fore.RED + f'Request_Error:{error_request_count}')
            with open('eror_request.txt','a+') as errors:
                errors.write(str(e))

        except Exception as e:
            error_count+=1
            progress.write(Fore.RED + f'Error:{error_request_count}')
            with open('errors.txt','a+') as error_c:
                error_c.write(str(e))
        # Обновляем прогресс-бар
        progress.update(1)
        
        #Done Task
        lines_queue.task_done()

def get_args():
    parser=argparse.ArgumentParser()
    parser.add_argument('-u','--url',help='Target Url')
    parser.add_argument('-w','--wordlists',help='Path to wordlist',default='/home/mamay/wordlists_for_rai/wordlist.txt')
    parser.add_argument('-t','--threads',help='The count of threads',default=25)
    parser.add_argument('-tm','--timeout',help='The timeout count',default=5)

    #запрашиваем интерактивно , если не передан аргумент
    args = parser.parse_args()
    if not args.url:
        args.url = input(Fore.YELLOW + 'Введите URL:\n')

    return args

def main():

    args = get_args()
    target_url = args.url 
    wordlists = args.wordlists
    thread_s = int(args.threads)
    timeout=int(args.timeout)

    try:
        with open(wordlists, 'r', encoding='utf-8') as filee:
            lines = sum(1 for _ in filee)
    except FileNotFoundError:
        print(Fore.RED + Style.BRIGHT + f"Файл {wordlists} не найден!")
        return
    
    if lines == 0:
        print(Fore.RED + Style.BRIGHT + "Файл пуст!")
        return
    
    print(Fore.YELLOW+ Style.BRIGHT +f"[+]Загружено {lines} words для фаззинга из словаря")
    # Загружаем все строки в очередь
    global lines_queue
    lines_queue = queue.Queue()
    
    with open(wordlists, 'r', encoding='utf-8') as f:
        for line in f:
            lines_queue.put(line.strip())
    
    #  прогресс-бар
    progress = tqdm(total=lines, desc="Fuzzing", unit="req")
    
    queue_lock = threading.Lock()
    
    # Создаем и запускаем потоки
    threads = []
    for i in range(thread_s):
        t = Thread(
            target=fuzz,
            args=(target_url, progress, queue_lock,timeout), 
            name=f"Fuzzer-{i}"
        )
        t.daemon = False  # Даем потокам завершиться нормально
        t.start()
        threads.append(t)
    print(Fore.RED + Style.BRIGHT + 'DEFAULT_THREADS: 25')
    print(Fore.YELLOW + Style.BRIGHT + f"Запущено {thread_s} потоков...")
    
    # Ждем завершения всех задач в очереди
    lines_queue.join()
    
    # Ждем завершения потоков
    for t in threads:
        t.join(timeout=1)  # Таймаут на случай проблем
    
    progress.close()
    print(Fore.GREEN + Style.BRIGHT + "[+] Done !")
    print(Fore.CYAN + 'Интересующие коды будут сохранены в файл report.txt')

if __name__ == "__main__":
    main()
