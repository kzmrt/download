from django.http import HttpResponse
from django.views import generic
from .models import Location, WeatherData
from django.contrib.auth.mixins import LoginRequiredMixin
import io
import matplotlib.pyplot as plt
import logging
from django.http import HttpResponseServerError
from django.shortcuts import render, redirect
import os
from .forms import UploadFileForm
from monitor import addCsv
import csv
from django.http import StreamingHttpResponse

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__)) + '/uploads/'  # アップロードしたファイルを保存するディレクトリ

logger = logging.getLogger('development')


class IndexView(LoginRequiredMixin, generic.ListView):
    model = Location
    paginate_by = 5
    ordering = ['-updated_at']
    template_name = 'monitor/index.html'


class DetailView(generic.DetailView):
    model = Location
    template_name = 'monitor/detail.html'


def my_test_500_view(request):
    # Return an "Internal Server Error" 500 response code.
    return HttpResponseServerError


# グラフ作成
def setPlt(pk):
    # 折れ線グラフを出力

    weather_data = WeatherData.objects.select_related('location').filter(location_id=pk)  # 対象ロケーションの気象データを取得
    # weather_data = WeatherData.objects.raw('SELECT * FROM weather_data WHERE location_id = %s', str(pk)) # このクエリでもOK
    x = [data.data_datetime for data in weather_data]  # 日時
    y1 = [data.temperature for data in weather_data]  # 気温
    y2 = [data.humidity for data in weather_data]  # 湿度
    """
    # 横に3つのグラフを並べる：axes([左, 下, 幅, 高さ])
    plt.axes([0.5, 0.5, 1.0, 1.0])  # 1つ目のグラフ
    plt.plot(x, y1, x, y2)
    plt.axes([1.7, 0.5, 1.0, 1.0])  # 2つ目のグラフ
    plt.plot(x, y1)
    plt.axes([2.9, 0.5, 1.0, 1.0])  # 3つ目のグラフ
    plt.plot(x, y2)
   """
    """
    # 縦に3つのグラフを並べる：axes([左, 下, 幅, 高さ])
    plt.axes([0.5, 2.4, 1.0, 1.0])  # 1つ目のグラフ
    plt.plot(x, y1, x, y2)

    plt.axes([0.5, 1.2, 1.0, 1.0])  # 2つ目のグラフ
    plt.plot(x, y1)

    plt.axes([0.5, 0.0, 1.0, 1.0])  # 3つ目のグラフ
    plt.plot(x, y2)
   """

    # 2×2のレイアウトに配置する
    fig = plt.figure(figsize=(15, 10))
    row = 2
    col = 2

    fig.add_subplot(row, col, 1)
    plt.plot(x, y1, x, y2)

    fig.add_subplot(row, col, 3)
    plt.plot(x, y1)

    fig.add_subplot(row, col, 4)
    plt.plot(x, y2)


# svgへの変換
def pltToSvg():
    buf = io.BytesIO()
    plt.savefig(buf, format='svg', bbox_inches='tight')
    s = buf.getvalue()
    buf.close()
    return s


def get_svg(request, pk):
    setPlt(pk)  # create the plot
    svg = pltToSvg()  # convert plot to SVG
    plt.cla()  # clean up plt so it can be re-used
    response = HttpResponse(svg, content_type='image/svg+xml')
    return response


# アップロードされたファイルのハンドル
def handle_uploaded_file(f):

    # アップロード用のディレクトリが存在するか確認
    # 存在しない場合、作成する。
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    path = os.path.join(UPLOAD_DIR, f.name)
    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    try:
        addCsv.insert_csv_data(path)  # csvデータをDBに登録する
    except Exception as exc:
        logger.error(exc)

    os.remove(path)  # アップロードしたファイルを削除


# ファイルアップロード
def upload(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_uploaded_file(request.FILES['file'])
            return redirect('monitor:upload_complete')  # アップロード完了画面にリダイレクト
    else:
        form = UploadFileForm()
    return render(request, 'monitor/upload.html', {'form': form})


# ファイルアップロード完了
def upload_complete(request):
    return render(request, 'monitor/upload_complete.html')


# データのダウンロード
def download(request, pk):

    # レスポンスの設定
    response = HttpResponse(content_type='text/csv')
    filename = 'data.csv'  # ダウンロードするcsvファイル名
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
    writer = csv.writer(response)

    # ヘッダー出力
    header = ['id','data_datetime','temperature','humidity','location_id']
    writer.writerow(header)

    # データ出力
    weather_data = WeatherData.objects.select_related('location').filter(location_id=pk)  # 対象ロケーションの気象データを取得
    for data in weather_data:
        writer.writerow([data.id, data.data_datetime, data.temperature, data.humidity, data.location_id])

    return response


class Echo:
    def write(self, value):
        return value


# クエリを少しずつ実行
def yield_query(query):
    filter_id = 0

    # ヘッダー出力
    yield ['id', 'data_datetime', 'temperature', 'humidity', 'location_id']

    while True:
        rows = list(query.filter(id__gt=filter_id).order_by('id')[:2])

        if len(rows) == 0:
            break

        for row in rows:
            yield [row.id, row.data_datetime, row.temperature, row.humidity, row.location_id]  # データ

        filter_id = rows[-1].id


# データのダウンロード（ストリーミング）
def some_streaming_csv_view(request, pk):

    query = WeatherData.objects.select_related('location').filter(location_id=pk)
    rows = yield_query(query) # クエリを少しずつ実行

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)

    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                     content_type="text/csv")
    filename = 'data.csv'  # ダウンロードするcsvファイル名
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    return response
