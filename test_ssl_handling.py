#!/usr/bin/env python3
"""
测试 SSL/TLS 请求处理
"""
import sys
import socket

def test_ssl_request():
    """模拟 SSL/TLS ClientHello 请求"""
    print("🔍 Testing SSL/TLS request handling...")

    # TLS 1.2 ClientHello 的开头字节
    tls_hello = b'\x16\x03\x01\x00\x05\x01\x00\x00\x01\x03'

    try:
        # 连接到服务器
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 8311))

        # 发送 TLS ClientHello
        sock.send(tls_hello)

        # 接收响应
        response = sock.recv(1024)
        sock.close()

        # 检查响应
        if response:
            print("✅ Server responded to SSL/TLS request")
            print(f"📦 Response preview: {response[:100]}")

            # 检查是否是 HTTP 400 响应
            if b'400' in response or b'Bad Request' in response:
                print("✅ Server correctly rejected SSL/TLS with 400 Bad Request")
                return True
            else:
                print("⚠️  Server responded but not with expected error")
                return False
        else:
            print("❌ No response received")
            return False

    except socket.timeout:
        print("⏱️  Connection timeout - server may not be running")
        return False
    except ConnectionRefusedError:
        print("❌ Connection refused - server is not running on port 8311")
        print("💡 Start the server with: python fund_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("SSL/TLS Request Handler Test")
    print("=" * 60)
    print("This script tests if the server properly handles SSL/TLS requests")
    print("sent to an HTTP endpoint.\n")

    result = test_ssl_request()

    print("\n" + "=" * 60)
    if result:
        print("✅ TEST PASSED - Server handles SSL/TLS requests correctly!")
    else:
        print("⚠️  TEST INCOMPLETE - Please ensure server is running")
    print("=" * 60)

    sys.exit(0 if result else 1)
