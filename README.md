抓取tumblr

管理博客功能:包括新增,启用追加更新,停用追加更新,统一通过命令行操作
(获取博客信息时,返回404自动停用博客状态)
python3 blog.py add xxx 新增博客
python3 blog.py show    展示所有博客
python3 blog.py show  xxx  展示指定博客
python3 blog.py stop xxx 停用博客
python3 blog.py start xxx 启用博客
使用pytumblr获取自己账号的关注列表.进而更新博客数据
python3 blog.py update    更新博客

每日追加更新模式:获取今日未更新过的博客的博文,如果发现已经获取过的博文,终止更新
python3 daily.py 10 更新10个,今日未更新的博客

单个更新:针对单个博客进行博文获取.包括强制更新和追加更新
python3 one.py xxx all
python3 one.py xxx new

多线程博文下载:采用多线程下载博文,博文根据博客名分文件夹.再根据发布日期分文件夹
python3 download.py 1000 10 启动10个线程下载1000个博文

初始化功能:初始化数据库和文件夹

日志记录:博客更新和博文下载都记录日志
日志文件夹:log

