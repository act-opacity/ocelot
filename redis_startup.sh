# ensure UNIX LF
redis-server /usr/local/etc/redis/redis.conf
echo  ""
echo  "\tRedis started as background process/daemon."
echo  "\tUsing configuration file copied during docker build"
echo  "\tSee redis.conf file here: /usr/local/etc/redis/redis.conf"
echo  ""
echo  "\tRunning flushdb on current Redis DB to ensure stale tasks are removed on startup."
redis-cli flushdb
echo  ""
echo  "\tRunning process to keep container alive."
tail -f /dev/null
