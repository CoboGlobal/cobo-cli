Run unit test
====

1. 在本地运行redis服务，保证`127.0.0.1:6379`可以连接redis服务

2. 运行单元测试

```
# 项目根目录下
$> tests/testenv/run_unittest.sh

# 重建tox环境
$> tests/testenv/run_unittest.sh -r
```

