#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 双校验位错误检测
========================================================

实验流程：
1. 生成正确汉明码
2. 随机改两个校验位（注入双位错误）
3. 计算校验子
4. 检查校验子是否能锁定错误位置

理论：
- 校验子 = 出错位的位置
- 改两个校验位 → 校验子应该是这两个位置的异或
"""

import numpy as np
from datetime import datetime

class DoubleParityError:
    def __init__(self):
        self.data_pos = [0, 1, 2, 3]
        self.parity_pos = [4, 5, 6]

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 双校验位错误检测")
        print("=" * 60)

    def encode(self, data):
        """4位数据编码为7位汉明码"""
        code = [0] * 7
        for i, d in enumerate(data):
            code[i] = d
        code[4] = code[0] ^ code[1] ^ code[2]
        code[5] = code[0] ^ code[2] ^ code[3]
        code[6] = code[1] ^ code[2] ^ code[3]
        return code

    def syndrome(self, code):
        """计算校验子"""
        s0 = code[4] ^ code[0] ^ code[1] ^ code[2]
        s1 = code[5] ^ code[0] ^ code[2] ^ code[3]
        s2 = code[6] ^ code[1] ^ code[2] ^ code[3]
        syndrome = (s2 << 2) | (s1 << 1) | s0
        return syndrome

    def inject_double_parity_error(self, code):
        """注入两个校验位错误"""
        err_code = code.copy()
        p_positions = [4, 5, 6]

        # 随机选两个校验位
        error_positions = np.random.choice(p_positions, 2, replace=False)

        for pos in error_positions:
            err_code[pos] ^= 1

        return err_code, list(error_positions)

    def run_trial(self):
        """单次试验"""
        data = [np.random.randint(0, 2) for _ in range(4)]
        original = self.encode(data)

        with_error, error_pos = self.inject_double_parity_error(original)

        syndrome = self.syndrome(with_error)

        return {
            'data': data,
            'original': original,
            'error_pos': error_pos,
            'with_error': with_error,
            'syndrome': syndrome,
        }

    def run(self, n=100):
        """运行n次试验"""
        print(f"运行 {n} 次试验...")
        results = []
        for i in range(n):
            results.append(self.run_trial())
            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")

        print(f"\n基本统计:")
        print(f"  总实验: {total}")

        # 校验子分布
        syndrome_counts = {}
        for r in results:
            s = r['syndrome']
            syndrome_counts[s] = syndrome_counts.get(s, 0) + 1

        print(f"\n校验子分布:")
        for s in sorted(syndrome_counts.keys()):
            print(f"  校验子{s}: {syndrome_counts[s]}次")

        # 检查校验子是否为错误位的线性组合
        print(f"\n校验子与错误位关系:")
        correct_syndrome = 0
        for r in results:
            ep = r['error_pos']
            # 两个校验位异或
            expected = ep[0] ^ ep[1]
            if r['syndrome'] == expected:
                correct_syndrome += 1

        print(f"  校验子=错误位异或的次数: {correct_syndrome}/{total}")

        return {'total': total, 'syndrome_counts': syndrome_counts}

    def show_examples(self, results, n=6):
        """展示例子"""
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  数据:   {r['data']}")
            print(f"  原始:   {r['original']}")
            print(f"  错误位: {r['error_pos']}")
            print(f"  错误码: {r['with_error']}")
            print(f"  校验子: {r['syndrome']}")
            expected = r['error_pos'][0] ^ r['error_pos'][1]
            print(f"  期望:   {expected} (错误位异或)")


def main():
    exp = DoubleParityError()
    results = exp.run(n=100)
    exp.show_examples(results, n=6)
    exp.analyze(results)


if __name__ == "__main__":
    main()