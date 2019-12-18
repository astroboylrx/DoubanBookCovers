import sys
import requests
import json
import matplotlib.pyplot as plt
from datetime import datetime as dt
from PIL import Image
from io import BytesIO
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSlot

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

        self.user_label = QtWidgets.QLabel('用户id', self)
        self.user_label.setGeometry(QtCore.QRect(40, 25, 41, 25))
        self.user_label.setAlignment(QtCore.Qt.AlignCenter)
        self.user_label.setObjectName("user_label")

        self.user_id = QtWidgets.QPlainTextEdit('user_id_12345', self)
        self.user_id.setGeometry(QtCore.QRect(50, 65, 220, 30))
        self.user_id.setObjectName("user_id")

        self.date1_label = QtWidgets.QLabel("起始日期 (格式:YYYY-MM-DD)", self)
        self.date1_label.setGeometry(QtCore.QRect(40, 130, 181, 25))
        self.date1_label.setAlignment(QtCore.Qt.AlignCenter)
        self.date1_label.setObjectName("date1_label")

        self.start_date = QtWidgets.QPlainTextEdit('2019-01-01', self)
        self.start_date.setGeometry(QtCore.QRect(50, 170, 220, 30))
        self.start_date.setObjectName("start_date")

        self.date2_label = QtWidgets.QLabel("终止日期 (格式:YYYY-MM-DD)", self)
        self.date2_label.setGeometry(QtCore.QRect(40, 235, 181, 25))
        self.date2_label.setAlignment(QtCore.Qt.AlignCenter)
        self.date2_label.setObjectName("date2_label")
        
        self.end_date = QtWidgets.QPlainTextEdit('2019-12-31', self)
        self.end_date.setGeometry(QtCore.QRect(50, 265, 220, 30))
        self.end_date.setObjectName("end_date")

        self.column_label = QtWidgets.QLabel("封面墙分几列（每行几本书）", self)
        self.column_label.setGeometry(QtCore.QRect(40, 330, 181, 25))
        self.date2_label.setAlignment(QtCore.Qt.AlignCenter)
        self.date2_label.setObjectName("column_label")

        self.num_cln = QtWidgets.QPlainTextEdit('5', self)
        self.num_cln.setGeometry(QtCore.QRect(50, 360, 220, 30))
        self.num_cln.setObjectName("num_cln")

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
        self.uid = self.user_id.toPlainText()
        self.date1 = self.start_date.toPlainText()
        self.date2 = self.end_date.toPlainText()
        
        try:
            self.books_per_row = int(self.num_cln.toPlainText())
            if self.books_per_row < 0:
                raise ValueError("Negative integer is not allowed")
        except ValueError as e:
            print(e)
            QtWidgets.QMessageBox.question(self, "Warning", "请在“封面墙分几列”里输入正整数", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return None

        self.progress.setValue(5)
        QtWidgets.QApplication.processEvents()

        res = self.get_read()
        
        if type(res) is int:
            if res == 1:
                QtWidgets.QMessageBox.question(self, "Warning", "日期格式有误", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
                return None
            elif res == 2:
                QtWidgets.QMessageBox.question(self, "Warning", "无法获取数据，请检查用户id是否正确", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
                return None
            elif res == 3:
                QtWidgets.QMessageBox.information(self, "Info", "豆瓣说在此期间没有阅读记录", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
                return None
            elif res == 4:
                QtWidgets.QMessageBox.information(self, "Warning", "目前的apikey失效了：豆瓣可能更换或关闭了访问数据的端口，暂时无能为力了", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
                return None
            elif res == 5:
                QtWidgets.QMessageBox.question(self, "Warning", "可能获取数据失败，总之程序出错了", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
                return None
            else:
                QtWidgets.QMessageBox.question(self, "Warning", "可能获取数据失败，总之程序出错了", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
                return None
        
        save_dialog = QtWidgets.QFileDialog()
        save_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        book_cover_path = save_dialog.getSaveFileName(self, '保存封面墙图片', str(Path.home())+"/封面墙.jpg", 
                                                      filter='JPEG Files(*.jpg);; PNG Files(*.png)')
        
        self.progress.setValue(75)
        QtWidgets.QApplication.processEvents()  
        res.savefig(book_cover_path[0], dpi=200)

        month_records = [0] * 12
        for i, item in enumerate(self.data['collections']):
            if 'updated' in item:
                month_records[int(item['updated'][5:7])-1] += 1
        
        self.progress.setValue(85)
        QtWidgets.QApplication.processEvents()

        fig, ax = plt.subplots(figsize=(8, 6))
        plt.rcParams.update({'font.size': 18})
        ax.bar(list(range(1, 13)), month_records)
        ax.set_xticks([1,2,3,4,5,6,7,8,9,10,11,12])
        ax.set_xlabel("Month"); ax.set_ylabel("# of Books Read"); ax.set_title("Report")
        ax.grid()

        book_cover_path = save_dialog.getSaveFileName(self, '保存月度阅读统计', str(Path.home())+"/月度阅读统计.jpg", 
                                                      filter='JPEG Files(*.jpg);; PNG Files(*.png)')

        fig.savefig(book_cover_path[0], bbox_inches='tight')

        self.progress.setValue(95)
        QtWidgets.QApplication.processEvents()
        
        try:
            total_pages = 0
            total_price = 0
            rating = [0, 0, 0, 0, 0]
            for i, item in enumerate(self.data['collections']):
                if 'rating' in item:
                    try:
                        rating[int(item['rating']['value'])-1] += 1
                    except Exception as e:
                        print(e)
                if 'pages' in item['book']:
                    try:
                        if item['book']['pages'][-1] == '页':
                            item['book']['pages'] = item['book']['pages'][:-1]
                        if item['book']['pages'][-1] == '頁':
                            item['book']['pages'] = item['book']['pages'][:-1]
                        total_pages += int(item['book']['pages'])
                    except Exception as e:
                        print(e)
                if 'price' in item['book']:
                    try:
                        if len(item['book']['price']) > 4:
                            if item['book']['price'][-1] == '元':
                                item['book']['price'] = item['book']['price'][:-1]
                            elif item['book']['price'][:3] == 'CNY':
                                item['book']['price'] = item['book']['price'][3:]
                            elif item['book']['price'][:3] == 'USD':
                                item['book']['price'] = str(float(item['book']['price'][3:]) * 6.8)
                            elif item['book']['price'][0] == '$':
                                item['book']['price'] = str(float(item['book']['price'][1:]) * 6.8)
                            elif item['book']['price'][:3] == 'GBP':
                                item['book']['price'] = str(float(item['book']['price'][3:]) * 9.0)
                            elif item['book']['price'][:3] == 'NTD':
                                item['book']['price'] = str(float(item['book']['price'][3:]) / 5.0)
                            elif item['book']['price'][:3] == 'NT$':
                                item['book']['price'] = str(float(item['book']['price'][3:]) / 5.0)
                            elif item['book']['price'][:3] == 'HKD':
                                item['book']['price'] = str(float(item['book']['price'][3:]) * 0.9)
                            tmp_price = float(item['book']['price'])
                            total_price += tmp_price
                    except Exception as e:
                        print(e)
            
            total_days = (dt.strptime(self.date2, "%Y-%m-%d") - dt.strptime(self.date1, "%Y-%m-%d")).days
            QtWidgets.QMessageBox.information(self, "Info", 
                "您总共读了 {} 本书\n平均 {:.2f} 天读一本\n合计 {} 页，约 {} 元\n其中您给\n{} 本书打了五星\n{} 本书打了四星\n{} 本书打了三星\n{} 本书打了二星\n{} 本书打了一星".format(self.num_books, total_days/self.num_books, total_pages, total_price, rating[4], rating[3], rating[2], rating[1], rating[0]))

            self.progress.setValue(100)
            QtWidgets.QApplication.processEvents()
        except Exception as e:
            print(e)
            QtWidgets.QMessageBox.question(self, "Warning", "尝试获取总页数、总价格，出错了", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok) 
            return None

    def get_read(self):

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

        self.url = "https://api.douban.com/v2/book/user/"+self.uid+"//collections?status=read&from="+self.date1+"T00:00:00+08:00&to="+self.date2+"T00:00:00+08:00&count=30&start=0&apikey=0df993c66c0c636e29ecbb5344252a4a"
        self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
        
        self.progress.setValue(15)
        QtWidgets.QApplication.processEvents()
        self.raw_data = requests.get(self.url, headers={'User-Agent': self.user_agent})
        self.raw_data.encoding = 'utf-8'
        self.data = json.loads(self.raw_data.text)

        self.progress.setValue(25)
        QtWidgets.QApplication.processEvents()

        if 'msg' in self.data:
            if self.data['msg'] == 'uri_not_found':
                return 2
            if self.data['msg'].find("invalid_apikey") != -1:
                return 4
        
        if 'total' in self.data:
            if int(self.data['total']) == 0:
                return 3

        self.progress.setValue(30)
        QtWidgets.QApplication.processEvents()
        try:
            self.num_books = int(self.data['total'])
            if self.num_books > 30:
                
                tmp_messagebox = TimerMessageBox("书本数量比较多，请耐心等待", timeout=3, parent=self)
                tmp_messagebox.exec_()

                tmp_start = 30
                tmp_remaining = self.num_books - 30
                while tmp_remaining > 0:
                    self.url = "https://api.douban.com/v2/book/user/"+self.uid+"//collections?status=read&from="+self.date1+"T00:00:00+08:00&to="+self.date2+"T00:00:00+08:00&count=100&start="+str(tmp_start)+"&apikey=0df993c66c0c636e29ecbb5344252a4a"
                    self.raw_data = requests.get(self.url, headers={'User-Agent': self.user_agent})
                    self.raw_data.encoding = 'utf-8'
                    self.data['collections'].extend(json.loads(self.raw_data.text)['collections'])
                    tmp_start += 100
                    tmp_remaining -= 100
            
            self.progress.setValue(40)
            QtWidgets.QApplication.processEvents()
            
            # get all images for books
            self.book_covers = []
            for i, item in enumerate(self.data['collections']):
                img_url = item['book']['image']
                self.book_covers.append(Image.open(BytesIO(requests.get(img_url, headers={'User-Agent': self.user_agent}).content)))
                self.book_covers[-1].thumbnail((500, 325), Image.ANTIALIAS)
            
            self.progress.setValue(55)
            QtWidgets.QApplication.processEvents()
            
            # now draw the cover wall!
            item_per_row = self.books_per_row
            num_rows = self.num_books // item_per_row
            if self.num_books % item_per_row > 0:
                num_rows += 1
            
            self.progress.setValue(65)
            QtWidgets.QApplication.processEvents()
            
            fig = plt.figure(figsize=(item_per_row*325/200, num_rows*500/200), dpi=200)
            row_height = 1-1/num_rows
            for i in range(self.num_books):
                #print([i%6*(1/6), i//6*0.2, 1/6, 0.2])
                ax = fig.add_axes(plt.Axes(fig, [i%item_per_row*(1/item_per_row), row_height-(i//item_per_row*(1/num_rows)), 1/item_per_row, 1/num_rows]))
                ax.imshow(self.book_covers[i], aspect='auto')
                ax.axis('off')
                
            fig.subplots_adjust(hspace=0, wspace=0)
            return fig
        
        except Exception as e:
            print(e)
            return 5
 
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    #app.setStyle("Fusion")
    ex = App()
    sys.exit(app.exec_())