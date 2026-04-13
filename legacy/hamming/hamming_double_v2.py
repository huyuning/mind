#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 双校验位错误检测（标准位置）
========================================================

标准汉明码位置：
- 位置1,2,4 = 校验位 (2^0, 2^1, 2^2)
- 位置0,3,5,6 = 数据位

校验方程：
- P0(位置1) = D0 ⊕ D1 ⊕ D3
- P1(位置2) = D0 ⊕ D2 ⊕ D3
- P2(位置4) = D1 ⊕ D2 ⊕ D3

实验：改两个校验位，看校验子
"""

import numpy as np
from datetime import datetime

class DoubleParityStandard:
    def __init__(self):
        # 标准位置定义
        self.data_pos = [0, 3, 5, 6]
        self.parity_pos = [1, 2, 4]

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 双校验位错误检测")
        print("=" * 60)
        print(f"数据位位置: {self.data_pos}")
        print(f"校验位位置: {self.parity_pos}")

    def encode(self, data):
        """4位数据编码为7位标准汉明码"""
        code = [0] * 7

        D0, D1, D2, D3 = data[0], data[1], data[2], data[3]

        code[0] = D0
        code[3] = D1
        code[5] = D2
        code[6] = D3

        code[1] = D0 ^ D1 ^ D3  # P0
        code[2] = D0 ^ D2 ^ D3  # P1
        code[4] = D1 ^ D2 ^ D3  # P2

        return code

    def syndrome(self, code):
        """计算校验子"""
        s0 = code[1] ^ code[0] ^ code[3] ^ code[5]  # P0 ⊕ D0 ⊕ D1 ⊕ D3
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]  # P1 ⊕ D0 ⊕ D2 ⊕ D3
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]  # P2 ⊕ D1 ⊕ D2 ⊕ D3

        syndrome = (s2 << 2) | (s1 << 1) | s0
        return syndrome

    def inject_double_parity_error(self, code):
        """注入两个校验位错误"""
        err_code = code.copy()
        error_positions = np.random.choice(self.parity_pos, 2, replace=False)

        for pos in error_positions:
            err_code[pos] ^= 1

        return err_code, sorted(list(error_positions))

    def run_trial(self):
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

        syndrome_counts = {}
        for r in results:
            s = r['syndrome']
            syndrome_counts[s] = syndrome_counts.get(s, 0) + 1

        print(f"\n校验子分布:")
        for s in sorted(syndrome_counts.keys()):
            print(f"  校验子{s} (二进制{s:03b}): {syndrome_counts[s]}次")

        # 检查校验子是否等于错误位置异或
        print(f"\n校验子与错误位关系:")
        matches = 0
        for r in results:
            ep = r['error_pos']
            expected = ep[0] ^ ep[1]
            if r['syndrome'] == expected:
                matches += 1

        print(f"  校验子=错误位异或: {matches}/{total} = {matches/total*100:.1f}%")

        return {'total': total, 'matches': matches}

    def show_examples(self, results, n=6):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            ep = r['error_pos']
            expected = ep[0] ^ ep[1]
            print(f"\n例子{i+1}:")
            print(f"  数据:   {r['data']}")
            print(f"  原始:   {r['original']}")
            print(f"  错误位: {ep}")
            print(f"  错误码: {r['with_error']}")
            print(f"  校验子: {r['syndrome']} (二进制{r['syndrome']:03b})")
            print(f"  期望:   {expected} (位{ep[0]}⊕位{ep[1]}={expected})")


def main():
    exp = DoubleParityStandard()
    results = exp.run(n=100)
    exp.show_examples(results, n=6)
    exp.analyze(results)


if __name__ == "__main__":
    main()