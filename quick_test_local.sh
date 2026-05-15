#!/bin/bash
# 一键测试本地抓包

echo "启动抓包（60秒）..."
sudo tcpdump -i en0 -s 0 -w test_$(date +%s).pcap host 216.167.34.54 &
PID=$!

echo "tcpdump PID: $PID"
echo "等待5秒让tcpdump初始化..."
sleep 5

echo ""
echo "现在请："
echo "1. 打开浏览器"
echo "2. 设置代理：socks5://127.0.0.1:10818"
echo "3. 访问 https://weibo.com 并浏览"
echo ""
echo "按Enter停止抓包..."
read

echo "停止抓包..."
sudo kill -TERM $PID
wait $PID

echo ""
echo "分析最新的pcap文件..."
LATEST=$(ls -t test_*.pcap | head -1)
echo "文件: $LATEST"
ls -lh "$LATEST"
echo ""
tshark -r "$LATEST" -q -z io,phs | head -30
