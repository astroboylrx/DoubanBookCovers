import os
import sys
import random
from datetime import datetime as dt
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSlot, QEventLoop, QTimer
from bs4 import BeautifulSoup
from subprocess import Popen, PIPE

def q_sleep(t_s):
    loop = QEventLoop()
    QTimer.singleShot(int(t_s * 1000), loop.quit)
    loop.exec_()

def get_from_safari(url):

    scpt = '''
            on run {input_url}
                tell application "Safari"
                    tell window 1
                        set current tab to (make new tab with properties {URL:input_url})
                        -- make sure the page is loaded
                        repeat while current tab's source = ""
                            delay 0.5
                        end repeat
                        -- wait a bit to make douban.com less suspicious
                        set delay_4_close to (random number from 2.5 to 6.0)
                        delay delay_4_close
                        set pageSource to the source of the current tab
                        close current tab
                    end tell
                end tell
                return pageSource
            end run'''
    
    p = Popen(['/usr/bin/osascript', '-'] + [url], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(scpt.encode('utf-8'))
    if stderr:
        try:
            err_text = stderr.decode("utf-8", errors="replace")
            cache_dir = Path.home() / "Library" / "Caches" / "DoubanBookCovers"
            cache_dir.mkdir(parents=True, exist_ok=True)
            with open(str(cache_dir / "stderr.log"), "a") as f:
                f.write(err_text + "\n")
        except Exception:
            pass
    return p.returncode, stdout, stderr

class BookInfo:
    
    def __init__(self, subject_item_source):
        """ Extract book info from the HTML list with class named subject-item in douban.com
            In the `contents` list of each item, [1] is <div class="pic">, [3] is <div class="info">
            
            An example pic div:
            <div class="pic">
                <a class="nbg" href="https://book.douban.com/subject/2336143/"
                    onclick="moreurl(this,{i:'0',query:'',subject_id:'2336143',from:'book_subject_search'})">
                    <img class="" src="https://img9.doubanio.com/view/subject/s/public/s2793303.jpg" width="90" />
                </a>
            </div>
            
            An example info div:
            <div class="info">
                <h2 class="">
                    <a href="https://book.douban.com/subject/2336143/"
                        onclick="moreurl(this,{i:'0',query:'',subject_id:'2336143',from:'book_subject_search'})" title="The Nine">

                        The Nine



                        <span style="font-size:12px;"> : Inside the Secret World of the Supreme Court </span>
                    </a>
                </h2>
                <div class="pub">


                    Jeffrey Toobin / Doubleday / 2007-9-18 / USD 32.50

                </div>
                <div class="short-note">
                    <div>
                        <span class="rating5-t"></span>
                        <span class="date">2020-01-01
                            读过</span>
                        <span class="tags">标签: NYPL</span>
                    </div>
                    <p class="comment">
                        Blah blah blah



                    </p>
                </div>
                <div class="ft">
                    <div class="cart-actions">
                        <span class="buy-info">
                            <a href="https://book.douban.com/subject/2336143/buylinks">
                                纸质版 189.14元起
                            </a>
                        </span>
                    </div>
                </div>
            </div>
        """
        
        self.c = subject_item_source.contents
        
        nbg_links = self.c[1].find_all('a', class_='nbg')
        self.book_url = nbg_links[0].attrs['href'][:-1] if nbg_links else ""
        self.book_ID = self.book_url[self.book_url.rfind('/')+1:] if self.book_url else ""
        self.book_cover_url = ""
        if getattr(self.c[1], "img", None) is not None and "src" in self.c[1].img.attrs:
            self.book_cover_url = self.c[1].img.attrs['src'].replace('s/public', 'l/public') # get larger image
        
        date_node = self.c[3].find('span', class_='date')
        self.complete_date = date_node.text.split('\n')[0] if date_node else ""
        title_node = self.c[3].find('a')
        self.book_title = title_node.text.replace('\n', '').lstrip().rstrip() if title_node else ""
        self.book_title = ' '.join(self.book_title.split())
        
        self.rating = None
        for i in range(5):
            tmp_rating = self.c[3].find_all('span', class_='rating'+str(i+1)+'-t')
            if len(tmp_rating) != 0:
                self.rating = i + 1
                break
        pub_node = self.c[3].find('div', class_='pub')
        self.price_info = ""
        if pub_node:
            self.price_info = pub_node.text.replace('\n', '').lstrip().rstrip().split(' / ')[-1]
    
    def __eq__(self, other):
        """ Overload comparison operator = """

        if not isinstance(other, BookInfo):
            raise TypeError("Comparison can only be done between BookInfo objects")
        return self.book_ID == other.book_ID

    def __ne__(self, other):
        """ Overload comparison operator != """

        if not isinstance(other, BookInfo):
            raise TypeError("Comparison can only be done between BookInfo objects")
        return self.book_ID != other.book_ID

    def get_more_info(self):
        
        """ This method easily triggers anti-crawling policy
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
        r = requests.get(self.book_url, headers=headers)
        if r.text.find("检测到有异常请求从你的 IP 发出") != -1:
            self.status_label.setText("豆瓣说访问太频繁，让我等60秒再试一次")
            QtWidgets.QApplication.processEvents()
            q_sleep(60)
            r = requests.get(self.book_url, headers=headers)
            if r.text.find("检测到有异常请求从你的 IP 发出") != -1:
                return 4
        """

        returncode, stdout, stderr = get_from_safari(self.book_url)
        if returncode != 0:
            return 11
        if stdout.decode('utf-8').find("检测到有异常请求从你的 IP 发出") != -1:
            return 4

        soup = BeautifulSoup(stdout, "html.parser")
        if (len(soup.find_all("div", id='info'))) > 0:
            self.info_list = soup.find_all("div", id='info')[0].text
            
            self.info_list = [x for x in [x.lstrip().rstrip() for x in self.info_list.split('\n')] if len(x) > 0]
            self.info_dict = {}; 
            i = 0
            while i < len(self.info_list):
                if self.info_list[i][-1] == ':' and i < len(self.info_list) - 1:
                    self.info_dict[self.info_list[i][:-1].lstrip().rstrip()] = self.info_list[i+1].lstrip().rstrip()
                    j = i + 2
                    while self.info_list[j].find(':') == -1 and j < len(self.info_list):
                        self.info_dict[self.info_list[i][:-1].lstrip().rstrip()] += self.info_list[j].lstrip().rstrip()
                        j += 1
                    i = j
                elif self.info_list[i].find(':') != -1:
                    tmp_list = self.info_list[i].split(':')
                    self.info_dict[tmp_list[0].lstrip().rstrip()] = tmp_list[1].lstrip().rstrip()
                    i += 1
                else:
                    print("Warning: there seems to be an invalid info entry: "+self.info_list[i]+" | proceed for now...")
                    i += 1
        else:
            self.info_list = []
            self.info_dict = {}
        if '页数' in self.info_dict:
            if self.info_dict['页数'][-1] == '页':
                self.info_dict['页数'] = self.info_dict['页数'][:-1]
        #print(self.info_list)
        #print(self.info_dict)
        return None

class TimerMessageBox(QtWidgets.QMessageBox):
    def __init__(self, msg, timeout=3, parent=None):
        super(TimerMessageBox, self).__init__(parent)
        self.setWindowTitle("Notice")
        self.time_to_wait = timeout
        self.msg = msg
        self.setText(self.msg+"（此提示会在 {0} 秒内自动关闭)".format(timeout))
        self.setStandardButtons(QtWidgets.QMessageBox.NoButton)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.changeContent)
        self.timer.start()

    def changeContent(self):
        self.setText(self.msg+"（此提示会在 {0} 秒内自动关闭)".format(self.time_to_wait))
        self.time_to_wait -= 1
        if self.time_to_wait <= 0:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()

class App(QtWidgets.QMainWindow):
 
    def __init__(self):
        super().__init__()
        self.title = '制作豆瓣读书封面墙'
        self.left = 400
        self.top = 200
        self.width = 320
        self.height = 480
        self.initUI()
 
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        label_x_pos = 40; label_height = 25
        inbox_x_pos = 50; inbox_height = 30
        gspace = label_height + 8 # group space
        hspace = inbox_height + 18

        self.user_label = QtWidgets.QLabel('用户id', self)
        self.user_label.setGeometry(QtCore.QRect(label_x_pos, 20, 41, label_height))
        self.user_label.setAlignment(QtCore.Qt.AlignCenter)
        self.user_label.setObjectName("user_label")

        nl = 1; ng = 0
        self.user_id = QtWidgets.QPlainTextEdit('user_id_12345', self)
        self.user_id.setGeometry(QtCore.QRect(inbox_x_pos, 20+nl*gspace+ng*hspace, 220, inbox_height))
        self.user_id.setObjectName("user_id")

        ng += 1
        self.date1_label = QtWidgets.QLabel("起始日期 (格式:YYYY-MM-DD)", self)
        self.date1_label.setGeometry(QtCore.QRect(label_x_pos, 20+nl*gspace+ng*hspace, 181, label_height))
        self.date1_label.setAlignment(QtCore.Qt.AlignCenter)
        self.date1_label.setObjectName("date1_label")

        nl += 1
        self.start_date = QtWidgets.QPlainTextEdit(dt.now().strftime("%Y-01-01"), self)
        self.start_date.setGeometry(QtCore.QRect(inbox_x_pos, 20+nl*gspace+ng*hspace, 220, inbox_height))
        self.start_date.setObjectName("start_date")

        ng += 1
        self.date2_label = QtWidgets.QLabel("终止日期 (格式:YYYY-MM-DD)", self)
        self.date2_label.setGeometry(QtCore.QRect(label_x_pos, 20+nl*gspace+ng*hspace, 181, label_height))
        self.date2_label.setAlignment(QtCore.Qt.AlignCenter)
        self.date2_label.setObjectName("date2_label")
        
        nl += 1
        self.end_date = QtWidgets.QPlainTextEdit(dt.now().strftime("%Y-%m-%d"), self)
        self.end_date.setGeometry(QtCore.QRect(inbox_x_pos, 20+nl*gspace+ng*hspace, 220, inbox_height))
        self.end_date.setObjectName("end_date")
        
        ng += 1
        self.column_label = QtWidgets.QLabel("封面墙分几列（每行几本书）", self)
        self.column_label.setGeometry(QtCore.QRect(label_x_pos, 20+nl*gspace+ng*hspace, 181, label_height))
        self.date2_label.setAlignment(QtCore.Qt.AlignCenter)
        self.date2_label.setObjectName("column_label")

        nl += 1
        self.num_cln = QtWidgets.QPlainTextEdit('5', self)
        self.num_cln.setGeometry(QtCore.QRect(inbox_x_pos, 20+nl*gspace+ng*hspace, 220, inbox_height))
        self.num_cln.setObjectName("num_cln")

        ng += 1
        self.stats_flag = QtWidgets.QCheckBox("是否统计总页数、价格（需运行更久）？", self)
        self.stats_flag.setGeometry(QtCore.QRect(label_x_pos-10, 20+nl*gspace+ng*hspace, 275, label_height))
        self.stats_flag.setObjectName("stats_flag")

        nl += 1
        self.status_label = QtWidgets.QLabel("首次运行时，请允许让我控制Safari来访问豆瓣", self)
        self.status_label.setGeometry(QtCore.QRect(20, 20+nl*gspace+ng*hspace, 280, label_height))
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setObjectName("status_label")

        self.gen_btn = QtWidgets.QPushButton('生成', self)
        self.gen_btn.setGeometry(QtCore.QRect(85, 420, 150, 40))
        self.gen_btn.setObjectName("gen_btn")
        self.gen_btn.clicked.connect(self.on_click)

        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setGeometry(QtCore.QRect(30, 455, 260, 25))
        self.progress.setObjectName("progress_bar")
        self.progress.setValue(0)

        self.show()

    @pyqtSlot()
    def on_click(self):
        import matplotlib.pyplot as plt

        self.uid = self.user_id.toPlainText()
        self.date1 = self.start_date.toPlainText()
        self.date2 = self.end_date.toPlainText()
        self.do_stats_flag = self.stats_flag.isChecked()
        
        try:
            self.books_per_row = int(self.num_cln.toPlainText())
            if self.books_per_row < 0:
                raise ValueError("Negative integer is not allowed")
        except ValueError as e:
            print(e)
            QtWidgets.QMessageBox.question(self, "Warning", "请在“封面墙分几列”里输入正整数", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return None

        self.progress.setValue(5)
        self.status_label.setText("准备中。。。")
        QtWidgets.QApplication.processEvents()
        
        res = self.get_read()
        if type(res) is int:
            self.handle_error(res)
            return None
        
        self.status_label.setText("封面墙绘制完成，请保存")
        QtWidgets.QApplication.processEvents()
        save_dialog = QtWidgets.QFileDialog()
        save_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        book_cover_path = save_dialog.getSaveFileName(self, '保存封面墙图片', str(Path.home())+"/封面墙.jpg", 
                                                      filter='JPEG Files(*.jpg);; PNG Files(*.png)')
        
        self.progress.setValue(75)
        if len(book_cover_path[0]) > 0:
            res.savefig(book_cover_path[0], dpi=200)
            self.status_label.setText("现在开始统计月度读书数量")
        else:
            self.status_label.setText("看来您取消了保存封面墙图片")
            QtWidgets.QApplication.processEvents()
            
            self.status_label.setText("现在开始统计月度读书数量")
        QtWidgets.QApplication.processEvents()

        month_records = [0] * 12
        for i, item in enumerate(self.valid_books):
            month_records[int(item.complete_date[5:7])-1] += 1

        fig, ax = plt.subplots(figsize=(8, 6))
        plt.rcParams.update({'font.size': 18})
        ax.bar(list(range(1, 13)), month_records)
        ax.set_xticks([1,2,3,4,5,6,7,8,9,10,11,12])
        ax.set_xlabel("Month"); ax.set_ylabel("# of Books Read"); ax.set_title("Report")
        ax.grid()
        
        self.progress.setValue(80)
        self.status_label.setText("月度阅读统计图绘制完成，请保存")
        QtWidgets.QApplication.processEvents()
        book_cover_path = save_dialog.getSaveFileName(self, '保存月度阅读统计', str(Path.home())+"/月度阅读统计.jpg", 
                                                      filter='JPEG Files(*.jpg);; PNG Files(*.png)')

        if len(book_cover_path[0]) > 0:
            fig.savefig(book_cover_path[0], bbox_inches='tight')
        else:
            self.status_label.setText("看来您取消了保存月度阅读统计图")
            QtWidgets.QApplication.processEvents()
            q_sleep(2)
        
        self.progress.setValue(82)
        QtWidgets.QApplication.processEvents()        

        # if stats
        if self.do_stats_flag:
            self.status_label.setText("现在收集更多书本数据进行统计")
            QtWidgets.QApplication.processEvents()

            try:
                total_pages = 0
                total_price = 0
                rating = [0, 0, 0, 0, 0]

                for i, item in enumerate(self.valid_books):
                    if item.rating is not None:
                        rating[item.rating-1] += 1

                    self.progress.setValue(min(82+int(15 * i / self.num_books), 97))
                    self.status_label.setText("从豆瓣图书获取：第"+str(i+1)+'/'+str(self.num_books)+"本"+'。'*(i%3+1))
                    QtWidgets.QApplication.processEvents() 
                    
                    try:
                        q_sleep(0.75 + random.random()) # let's wait a bit to make douban.com less suspicious
                        if i % 10 == 0:
                            q_sleep(45 + 10 * random.random()) # let's wait a bit to make douban.com less suspicious
                        res = item.get_more_info()
                        if type(res) is int:
                            self.handle_error(res)
                            continue
                    except Exception as e:
                        print(e)
                        continue

                    if '页数' in item.info_dict:
                        try:                
                            total_pages += int(item.info_dict['页数'])
                        except Exception as e:
                            print(e)
                            continue

                    if '定价' in item.info_dict:
                        tmp_price = item.info_dict['定价']
                        try:
                            if len(tmp_price) > 4:
                                if tmp_price[-1] == '元':
                                    tmp_price = tmp_price[:-1]
                                if tmp_price[0] == '¥':
                                    tmp_price = tmp_price[1:]
                                if tmp_price[:3] == 'CNY':
                                    tmp_price = tmp_price[3:]
                                if tmp_price[:3] == 'USD':
                                    tmp_price = str(float(tmp_price[3:]) * 7.0)
                                if tmp_price[0] == '$':
                                    tmp_price = str(float(tmp_price[1:]) * 7.0)
                                if tmp_price[:3] == 'GBP':
                                    tmp_price = str(float(tmp_price[3:]) * 9.4)
                                if tmp_price[:3] == 'NTD':
                                    tmp_price = str(float(tmp_price[3:]) / 4.5)
                                if tmp_price[-2:] == '台币':
                                    tmp_price = str(float(tmp_price[:-2]) / 4.5)
                                if tmp_price[:3] == 'NT$':
                                    tmp_price = str(float(tmp_price[3:]) / 4.5)
                                if tmp_price[:3] == 'HKD':
                                    tmp_price = str(float(tmp_price[3:]) * 0.9)
                                if tmp_price[:3] == 'HK$':
                                    tmp_price = str(float(tmp_price[3:]) * 0.9)
                                if len(tmp_price) > 0:
                                    tmp_price = float(tmp_price)
                                    total_price += tmp_price
                        except Exception as e:
                            print(e)
                            continue
                
                self.status_label.setText("成功获取所需图书数据")
                QtWidgets.QApplication.processEvents()
                total_days = (dt.strptime(self.date2, "%Y-%m-%d") - dt.strptime(self.date1, "%Y-%m-%d")).days
                QtWidgets.QMessageBox.information(self, "Info", 
                    self.user_name+": 感谢使用本软件！\n"+"据可能不完全的统计，您总共读了 {} 本书：\n平均 {:.2f} 天读一本\n合计 {} 页，约 {:.2f} 元\n其中您给\n{} 本书打了五星\n{} 本书打了四星\n{} 本书打了三星\n{} 本书打了二星\n{} 本书打了一星".format(self.num_books, total_days/self.num_books, total_pages, total_price, rating[4], rating[3], rating[2], rating[1], rating[0]))
            
            except Exception as e:
                print(e)
                QtWidgets.QMessageBox.question(self, "Warning", "尝试获取评分统计、总页数、总价格等数据时出错了", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
                return None
        else:
            self.status_label.setText("未选择更多统计，目标已完成。")
            QtWidgets.QApplication.processEvents()
            total_days = (dt.strptime(self.date2, "%Y-%m-%d") - dt.strptime(self.date1, "%Y-%m-%d")).days
            QtWidgets.QMessageBox.information(self, "Info", 
                    self.user_name+": 感谢使用本软件！\n"+"您总共读了 {} 本书：\n平均 {:.2f} 天读一本\n".format(self.num_books, total_days/self.num_books))

        self.progress.setValue(100)
        QtWidgets.QApplication.processEvents()
        return None        
    
    def get_read(self):
        import matplotlib.pyplot as plt
        import requests
        from PIL import Image
        from io import BytesIO

        try:
            self.__sd = dt.strptime(self.date1, "%Y-%m-%d")
            self.__ed = dt.strptime(self.date2, "%Y-%m-%d")
            if self.__sd > self.__ed:
                self.date1, self.date2 = self.date2, self.date1
        except Exception as e:
            print(e)
            return 1
        self.progress.setValue(10)
        QtWidgets.QApplication.processEvents()

        tmp_book_start_index = 0
        self.url = "https://book.douban.com/people/"+self.uid+"/collect?start="+str(tmp_book_start_index)+"&sort=time&rating=all&filter=all&mode=grid"
        returncode, stdout, stderr = get_from_safari(self.url)
        self.status_label.setText("访问豆瓣读书第"+str(tmp_book_start_index+1)+"次")
        QtWidgets.QApplication.processEvents()

        if returncode != 0:
            return 10
        if stdout.decode('utf-8').find("检测到有异常请求从你的 IP 发出") != -1:
            return 4
        soup = BeautifulSoup(stdout, "html.parser")
        
        # check if the user exist
        self.user_exist_flag = False
        if soup.find_all('title')[0].text == '页面不存在':
            return 2
        if soup.find_all('title')[0].text == '404 Not Found':
            return 21
        else:
            self.user_exist_flag = True
            self.user_info = soup.find_all('title')[0].text.replace('\n', '').lstrip().rstrip()
            self.user_name = self.user_info[:self.user_info.find("读过的书")]
            self.num_book_tot = int(self.user_info[self.user_info.find("(")+1:self.user_info.find(")")])
        self.progress.setValue(15)
        QtWidgets.QApplication.processEvents()

        # check if the user has reading history
        if self.num_book_tot == 0:
            return 31
        try:
            self.book_items = soup.find_all('li', class_='subject-item')
            self.books = [BookInfo(book) for book in self.book_items]
        except Exception as e:
            print(e)
            return 5
        self.progress.setValue(20)
        self.status_label.setText("成功获取并处理第"+str(tmp_book_start_index+1)+"页的内容")
        QtWidgets.QApplication.processEvents()

        if self.books[0].complete_date < self.date1:
            return 3

        while self.books[-1].complete_date >= self.date1 and len(self.books) < self.num_book_tot:
            q_sleep(2.5 + random.random()) # let's wait a bit to make douban.com less suspicious
            tmp_book_start_index += 1
            if tmp_book_start_index % 3 == 0:
                self.status_label.setText("需要搜寻的阅读历史较多，请耐心等待")
                QtWidgets.QApplication.processEvents()
                q_sleep(2)
                #tmp_messagebox = TimerMessageBox("需要搜寻的阅读历史较多，请耐心等待", timeout=2.5, parent=self)
                #tmp_messagebox.exec_()

            self.url = "https://book.douban.com/people/"+self.uid+"/collect?start="+str(tmp_book_start_index*15)+"&sort=time&rating=all&filter=all&mode=grid"
            self.status_label.setText("访问豆瓣读书第"+str(tmp_book_start_index+1)+"次")
            QtWidgets.QApplication.processEvents()
            returncode, stdout, stderr = get_from_safari(self.url)

            if returncode != 0:
                return 11
            if stdout.decode('utf-8').find("检测到有异常请求从你的 IP 发出") != -1:
                return 4

            try:
                soup = BeautifulSoup(stdout, "html.parser")
                tmp_book_items = soup.find_all('li', class_='subject-item')
                self.books += [BookInfo(book) for book in tmp_book_items]
                self.book_items.append(tmp_book_items)
                self.progress.setValue(min(20+tmp_book_start_index*2, 40))
                self.status_label.setText("成功获取并处理第"+str(tmp_book_start_index+1)+"页的内容")
                QtWidgets.QApplication.processEvents()
            except Exception as e:
                print(e)
                return 5

        self.progress.setValue(40)
        self.status_label.setText("内容初步获取完毕")
        QtWidgets.QApplication.processEvents()

        # find all books within date range
        self.valid_books = [book for book in self.books if (book.complete_date >= self.date1) and (book.complete_date <= self.date2)]
        self.num_books = len(self.valid_books)
        if self.num_books == 0:
            return 3
        
        # get all images for books
        self.status_label.setText("现在按序获取封面墙的"+str(self.num_books)+"图书封面")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            'Referer': 'https://book.douban.com/',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        }
        session = requests.Session()
        self.book_covers = []
        self.valid_books_with_covers = []
        total_books = self.num_books
        for i, item in enumerate(self.valid_books):
            q_sleep(0.5 + random.random())
            img_url = item.book_cover_url
            try:
                resp = None
                for attempt in range(3):
                    try:
                        resp = session.get(img_url, headers=headers, timeout=10)
                        if resp.status_code == 418 or resp.status_code == 403:
                            raise ValueError("Blocked status: " + str(resp.status_code))
                        resp.raise_for_status()
                        content_type = resp.headers.get("Content-Type", "")
                        if not content_type.startswith("image/"):
                            raise ValueError("Non-image content type: " + content_type)
                        break
                    except Exception:
                        if attempt < 2:
                            q_sleep(1 + attempt * 2 + random.random())
                            continue
                        raise
                img = Image.open(BytesIO(resp.content))
                img.thumbnail((500, 325), Image.Resampling.LANCZOS)
                self.book_covers.append(img)
                self.valid_books_with_covers.append(item)
            except Exception as e:
                print("Cover fetch failed: title={0} url={1} cover={2} err={3}".format(
                    item.book_title, item.book_url, img_url, e))
                continue

            self.progress.setValue(min(40+int(25 * i / total_books), 65))
            QtWidgets.QApplication.processEvents()
            self.status_label.setText("已获取"+str(i+1)+'/'+str(total_books)+"封面图片"+'。'*(i%3+1))

        self.valid_books = self.valid_books_with_covers
        self.num_books = len(self.valid_books)
        if self.num_books == 0:
            return 5
        
        self.progress.setValue(65)
        self.status_label.setText("成功获取所有封面墙所需图片！开始绘制。")
        QtWidgets.QApplication.processEvents()
        
        # now draw the cover wall!
        item_per_row = self.books_per_row
        num_rows = self.num_books // item_per_row
        if self.num_books % item_per_row > 0:
            num_rows += 1
                
        fig = plt.figure(figsize=(item_per_row*325/200, num_rows*500/200), dpi=200)
        row_height = 1-1/num_rows
        for i in range(self.num_books):
            #print([i%6*(1/6), i//6*0.2, 1/6, 0.2])
            ax = fig.add_axes(plt.Axes(fig, [i%item_per_row*(1/item_per_row), row_height-(i//item_per_row*(1/num_rows)), 1/item_per_row, 1/num_rows]))
            ax.imshow(self.book_covers[i], aspect='auto')
            ax.axis('off')
        
        self.progress.setValue(70)
        QtWidgets.QApplication.processEvents()

        fig.subplots_adjust(hspace=0, wspace=0)
        return fig

    def handle_error(self, error_code):
        
        self.status_label.setText("出错了。。。")
        QtWidgets.QApplication.processEvents()
        if error_code == 1:
            QtWidgets.QMessageBox.question(self, "Warning", "日期格式有误", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return None
        elif error_code == 10:
            QtWidgets.QMessageBox.question(self, "Warning", "似乎无法调用Safari浏览器，可能没有相关权限？", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return None
        elif error_code == 11:
            QtWidgets.QMessageBox.question(self, "Warning", "似乎无法调用Safari浏览器（可是之前已经成功调用过了，但是这次失败了。。。）", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return None
        elif error_code == 2:
            QtWidgets.QMessageBox.question(self, "Warning", "该用户似乎不存在，无法获取数据，请检查用户id是否正确", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None
        elif error_code == 21:
            QtWidgets.QMessageBox.question(self, "Warning", "豆瓣说:“Not Found。你要的东西不在这, 到别处看看吧。” 请检查用户id是否正确", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None
        elif error_code == 3:
            QtWidgets.QMessageBox.information(self, "Info", "豆瓣说"+self.user_name+"在此期间没有阅读记录", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None
        elif error_code == 31:
            QtWidgets.QMessageBox.information(self, "Info", "豆瓣说该用户没有阅读记录。。。", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None
        elif error_code == 4:
            QtWidgets.QMessageBox.information(self, "Warning", "豆瓣说：“检测到有异常请求从你的 IP 发出，请登录使用豆瓣”。大概率是访问太频繁了，请过一段时间再试。", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None
        elif error_code == 5:
            QtWidgets.QMessageBox.question(self, "Warning", "可能获取数据失败，总之程序出错了", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None
        else:
            QtWidgets.QMessageBox.question(self, "Warning", "可能获取数据失败，总之程序出错了", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    #app.setStyle("Fusion")
    ex = App()
    sys.exit(app.exec_())
