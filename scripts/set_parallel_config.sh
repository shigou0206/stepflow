#!/bin/bash
# 设置并行执行的配置

# 活动工作器数量
export NUM_ACTIVITY_WORKERS=4

# 每个工作器的最大并行任务数
export MAX_CONCURRENT_TASKS=10

# 启动服务
python -m stepflow.main 