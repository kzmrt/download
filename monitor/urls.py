from django.urls import path
from . import views

app_name = 'monitor'

urlpatterns = [
    # トップ画面
    path('', views.IndexView.as_view(), name='index'),

    # 詳細画面
    path('monitor/<int:pk>/', views.DetailView.as_view(), name='detail'),

    # グラフ描画
    path('monitor/<int:pk>/plot/', views.get_svg, name='plot'),

    # データダウンロード
    path('monitor/<int:pk>/download/', views.download, name='download'),

    # データダウンロード（ストリーミング）
    path('monitor/<int:pk>/streaming/', views.some_streaming_csv_view, name='streaming'),

    # ファイルアップロード用
    path('monitor/upload/', views.upload, name='upload'),
    path('monitor/upload_complete/', views.upload_complete, name='upload_complete'),
]