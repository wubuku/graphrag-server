#!/bin/bash

# GraphRAG 统一工具脚本
# 用法: ./graphrag_tool.sh [选项]
# 选项: install, fix, start, index, menu

CONDA_ENV_PATH="/opt/miniconda3/envs/graphrag/bin"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色信息
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 检查 conda 是否可用
check_conda() {
    if ! command -v conda &> /dev/null; then
        print_error "conda 未找到，请先安装 Miniconda 或 Anaconda"
        exit 1
    fi
}

# 激活环境并修复路径
fix_environment() {
    print_info "修复 Python 环境..."
    
    # 激活 conda 环境
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate graphrag
    
    # 修改 PATH，确保 conda 环境优先
    export PATH="$CONDA_ENV_PATH:$PATH"
    
    # 设置别名
    alias python="$CONDA_ENV_PATH/python"
    alias pip="$CONDA_ENV_PATH/pip"
    
    print_success "环境已修复"
    return 0
}

# 验证环境
verify_environment() {
    print_info "验证环境状态..."
    
    echo "📍 当前环境: $CONDA_DEFAULT_ENV"
    echo "🐍 Python: $(which python)"
    echo "📦 pip: $(which pip)"
    echo "🔧 Python 版本: $(python --version 2>&1)"
    
    # 测试模块导入
    echo ""
    print_info "测试模块导入:"
    python -c "import sys; print('✅ Python 路径:', sys.executable)" 2>/dev/null || print_error "Python 路径错误"
    python -c "import fastapi; print('✅ FastAPI 可用')" 2>/dev/null || print_warning "FastAPI 不可用"
    python -c "import graphrag; print('✅ GraphRAG 可用')" 2>/dev/null || print_warning "GraphRAG 不可用"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."
    
    if [[ ! -f "requirements.txt" ]]; then
        print_error "未找到 requirements.txt 文件"
        return 1
    fi
    
    # 使用绝对路径安装
    "$CONDA_ENV_PATH/pip" install -r requirements.txt
    
    if [[ $? -eq 0 ]]; then
        print_success "依赖安装完成"
        return 0
    else
        print_error "依赖安装失败"
        return 1
    fi
}

# 启动服务器
start_server() {
    print_info "启动 GraphRAG 服务器..."
    
    if [[ ! -d "webserver" ]]; then
        print_error "未找到 webserver 目录"
        return 1
    fi
    
    print_info "服务器启动中... (Ctrl+C 停止)"
    "$CONDA_ENV_PATH/python" -m webserver.main
}

# 运行索引
run_index() {
    print_info "运行 GraphRAG 索引..."
    
    if [[ ! -d "input" ]]; then
        print_warning "未找到 input 目录，正在创建..."
        mkdir -p input
        print_info "请将您的文档放入 input/ 目录"
        return 1
    fi
    
    if [[ ! -f "settings.yaml" ]]; then
        print_warning "未找到 settings.yaml 配置文件"
        print_info "请先配置 settings.yaml 文件"
        return 1
    fi
    
    "$CONDA_ENV_PATH/python" -m graphrag.index --root .
}

# 显示菜单
show_menu() {
    echo ""
    echo "🚀 GraphRAG 工具箱"
    echo "=================="
    echo "1. 🔧 修复环境 (推荐首次运行)"
    echo "2. 📦 安装依赖"
    echo "3. 🔍 验证环境"
    echo "4. 📊 运行索引"
    echo "5. 🌐 启动服务器"
    echo "6. 🏁 一键完整安装"
    echo "0. 🚪 退出"
    echo ""
    read -p "请选择操作 [0-6]: " choice
    
    case $choice in
        1) fix_and_verify ;;
        2) install_dependencies ;;
        3) verify_environment ;;
        4) run_index ;;
        5) start_server ;;
        6) full_install ;;
        0) print_info "再见！"; exit 0 ;;
        *) print_error "无效选择"; show_menu ;;
    esac
}

# 修复并验证
fix_and_verify() {
    check_conda
    fix_environment
    verify_environment
}

# 完整安装流程
full_install() {
    check_conda
    fix_environment
    install_dependencies
    verify_environment
    
    print_success "安装完成！"
    print_info "接下来的步骤:"
    echo "1. 将文档放入 input/ 目录"
    echo "2. 配置 settings.yaml"
    echo "3. 创建 .env 文件设置 API key"
    echo "4. 运行: $0 index"
    echo "5. 启动: $0 start"
}

# 主函数
main() {
    case "${1:-menu}" in
        "install"|"i")
            full_install
            ;;
        "fix"|"f")
            fix_and_verify
            ;;
        "start"|"s")
            fix_environment > /dev/null 2>&1
            start_server
            ;;
        "index"|"idx")
            fix_environment > /dev/null 2>&1
            run_index
            ;;
        "verify"|"v")
            fix_environment > /dev/null 2>&1
            verify_environment
            ;;
        "menu"|"m"|"")
            show_menu
            ;;
        "help"|"h"|"-h"|"--help")
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  install, i    - 完整安装（推荐）"
            echo "  fix, f        - 修复环境"
            echo "  start, s      - 启动服务器"
            echo "  index, idx    - 运行索引"
            echo "  verify, v     - 验证环境"
            echo "  menu, m       - 显示菜单（默认）"
            echo "  help, h       - 显示帮助"
            ;;
        *)
            print_error "未知选项: $1"
            echo "使用 '$0 help' 查看帮助"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 