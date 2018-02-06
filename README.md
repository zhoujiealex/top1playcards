# 功能
根据指定sessionId登录ICBC后，下载商户门店订单详细信息，并保存为excel文件。
- 指定日期（已完成）
- 指定时间段（待完成）

# TODO列表
- 创建sqlite和对应表模型
- 保存商户门店信息到db
- 保存门店订单详细信息到db
- 根据报单的excel/json导入报单的数据到DB
- 比对分析指定门店，指定日期的报单和实际数据差异

# 实现

- 利用requests包进行http请求
- 利用xlwt包保存excel文件


# 使用说明
1. 安装python环境，版本2.7
    
    > Windows直达链接（Python 2.7.14）
    https://www.python.org/ftp/python/2.7.14/python-2.7.14.msi
    
    > python下载： https://www.python.org/downloads/
    
    > 特别要注意选上`pip`和`Add python.exe to Path`，然后一路点“Next”即可完成安装。
    
    > 默认会安装到C:\Python27目录下.
    
    > 详细参考： [安装Python
](https://www.liaoxuefeng.com/wiki/001374738125095c955c1e6d8bb493182103fac9270762a000/001374738150500472fd5785c194ebea336061163a8a974000)

2. 安装依赖包， 执行程序目录下的 `install.bat`
3. 运行 `run.bat`，默认运行端口8888，访问： http://localhost:8888/
4. 输入正确session值后，保存的excel位于当前目录的`excels`文件下

    > 默认文件名称：<商户交易订单yyy-mm-dd>.xls



# Know Issues
1. xlwt生成的excel文件，版本在新的excel2010以上，第一次打开会报不兼容，不影响使用

    > "文件错误。可能某些数字格式已丢失。"


