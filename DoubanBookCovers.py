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
        
        self.genbtn = QtWidgets.QPushButton('生成', self)
        self.genbtn.setGeometry(QtCore.QRect(85, 420, 150, 40))
        self.genbtn.setObjectName("genbtn")
        self.genbtn.clicked.connect(self.on_click)

        self.userlabel = QtWidgets.QLabel('用户id', self)
        self.userlabel.setGeometry(QtCore.QRect(40, 40, 41, 25))
        self.userlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.userlabel.setObjectName("userlabel")
        self.date1label = QtWidgets.QLabel("起始日期 (格式:YYYY-MM-DD)", self)
        self.date1label.setGeometry(QtCore.QRect(40, 150, 181, 25))
        self.date1label.setAlignment(QtCore.Qt.AlignCenter)
        self.date1label.setObjectName("date1label")
        self.date2label = QtWidgets.QLabel("终止日期 (格式:YYYY-MM-DD)", self)
        self.date2label.setGeometry(QtCore.QRect(40, 260, 181, 25))
        self.date2label.setAlignment(QtCore.Qt.AlignCenter)
        self.date2label.setObjectName("date2label")
        self.user_id = QtWidgets.QPlainTextEdit('user_id_12345', self)
        self.user_id.setGeometry(QtCore.QRect(50, 80, 220, 30))
        self.user_id.setObjectName("user_id")
        self.start_date = QtWidgets.QPlainTextEdit('2018-01-01', self)
        self.start_date.setGeometry(QtCore.QRect(50, 190, 220, 30))
        self.start_date.setObjectName("start_date")
        self.end_date = QtWidgets.QPlainTextEdit('2018-12-01', self)
        self.end_date.setGeometry(QtCore.QRect(50, 300, 220, 30))
        self.end_date.setObjectName("end_date")
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
                    rating[int(item['rating']['value'])-1] += 1
                if 'pages' in item['book']:
                    if item['book']['pages'][-1] == '页':
                        item['book']['pages'] = item['book']['pages'][:-1]
                    total_pages += int(item['book']['pages'])
                if 'price' in item['book']:
                    try:
                        if len(item['book']['price']) > 0:
                            if item['book']['price'][-1] == '元':
                                item['book']['price'] = item['book']['price'][:-1]
                            tmp_price = float(item['book']['price'])
                            total_price += tmp_price
                    except Exception as e:
                        print(e)
            
            QtWidgets.QMessageBox.information(self, "Info", 
                "您总共读了 {} 本书\n平均 {:.2f} 天读一本\n合计 {} 页，约 {} 元\n其中您给\n{} 本书打了五星\n{} 本书打了四星\n{} 本书打了三星\n{} 本书打了二星\n{} 本书打了一星".format(self.num_books, 365/self.num_books, total_pages, total_price, rating[4], rating[3], rating[2], rating[1], rating[0]))

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

        self.url = "https://api.douban.com/v2/book/user/"+self.uid+"//collections?status=read&from="+self.date1+"T00:00:00+08:00&to="+self.date2+"T00:00:00+08:00&count=30"
        
        self.progress.setValue(15)
        QtWidgets.QApplication.processEvents()
        self.raw_data = requests.get(self.url)
        self.raw_data.encoding = 'utf-8'
        self.data = json.loads(self.raw_data.text)

        self.progress.setValue(25)
        QtWidgets.QApplication.processEvents()
        if 'msg' in self.data:
            if self.data['msg'] == 'uri_not_found':
                return 2
        
        if 'total' in self.data:
            if int(self.data['total']) == 0:
                return 3

        self.progress.setValue(30)
        QtWidgets.QApplication.processEvents()
        try:
            self.num_books = int(self.data['total'])
            if self.num_books > 30:
                self.url = "https://api.douban.com/v2/book/user/"+self.uid+"//collections?status=read&from="+self.date1+"T00:00:00+08:00&to="+self.date2+"T00:00:00+08:00&count="+str(2*self.num_books)
                self.raw_data = requests.get(self.url)
                self.raw_data.encoding = 'utf-8'
                self.data = json.loads(self.raw_data.text)

            self.progress.setValue(40)
            QtWidgets.QApplication.processEvents()
            
            # get all images for books
            self.book_covers = []
            for i, item in enumerate(self.data['collections']):
                img_url = item['book']['image']
                self.book_covers.append(Image.open(BytesIO(requests.get(img_url).content)))
                self.book_covers[-1].thumbnail((500, 325), Image.ANTIALIAS)
            
            self.progress.setValue(55)
            QtWidgets.QApplication.processEvents()

            # now draw the cover wall!
            item_per_row = 6
            num_rows = self.num_books // item_per_row
            if self.num_books % item_per_row > 0:
                num_rows += 1
            
            self.progress.setValue(65)
            QtWidgets.QApplication.processEvents()
            
            fig = plt.figure(figsize=(item_per_row*325/200, num_rows*500/200), dpi=200)
            for i in range(self.num_books):
                #print([i%6*(1/6), i//6*0.2, 1/6, 0.2])
                ax = fig.add_axes(plt.Axes(fig, [i%item_per_row*(1/item_per_row), i//item_per_row*(1/num_rows), 1/item_per_row, 1/num_rows]))
                ax.imshow(self.book_covers[i], aspect='auto')
                ax.axis('off')
                
            fig.subplots_adjust(hspace=0, wspace=0)
            return fig
        
        except Exception as e:
            print(e)
            return 4
 
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    #app.setStyle("Fusion")
    ex = App()
    sys.exit(app.exec_())