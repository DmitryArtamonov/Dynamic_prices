from datetime import datetime

class Log():

    def add(self, text, mode=''):  # mode = 'c' for console only, 'f' - for file only
        if mode != 'c':
            with open ('log.txt', mode='a', encoding='UTF-8') as log_file:
                print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] {text}", file=log_file)
        if mode != 'f':
            print(f'[log] {text}')


    def br(self):
        self.add('')

    def clear(self):
        with open ('log.txt', mode='w', encoding='UTF-8') as log_file:
            print('', end='', file=log_file)


log = Log()
