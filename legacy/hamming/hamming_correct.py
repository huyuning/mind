#!/usr/bin/env python3
"""
========================================================
正确汉明码纠缠实验
========================================================

正确实现汉明码：
- 数据位: 位置 0,1,2,3
- 校验位: 位置 4,5,6 (2^0, 2^1, 2^2)
- 校验子 = 错误位置

使用方法：
    python3 hamming_correct.py
"""

import numpy as np
from datetime import datetime

class CorrectHammingEntanglement:
    """
    正确实现的汉明码纠缠
    """

    def __init__(self):
        # 7位汉明码(4数据+3校验)
        # 位置:     0  1  2  3  4  5  6
        #           D0 P0 D1 D2 P1 D3 P2
        #
        # 校验位位置: 1, 2, 4 (即2^0, 2^1, 2^2)
        # 数据位位置: 0, 3, 5, 6
        #
        # 校验方程:
        # P0(位置1) = D0 ⊕ D1 ⊕ D2
        # P1(位置2) = D0 ⊕ D3 ⊕ P0
        # P2(位置4) = D1 ⊕ D3 ⊕ P0 ⊕ P1

        # 简化：重新定义位置
        # 位置:     0  1  2  3  4  5  6  7
        #           D0 D1 D2 D3 P0 P1 P2 P3
        #
        # P0(位置4) = D0 ⊕ D1 ⊕ D3
        # P1(位置5) = D0 ⊕ D2 ⊕ D3
        # P2(位置6) = D1 ⊕ D2 ⊕ D3
        # P3(位置7) = P0 ⊕ P1 ⊕ P2

        # 位置映射
        self.data_pos = [0, 1, 2, 3]  # 数据位
        self.parity_pos = [4, 5, 6, 7]  # 校验位

        # 每个校验位包含哪些数据位
        self.parity_to_data = {
            4: [0, 1, 3],  # P0
            5: [0, 2, 3],  # P1
            6: [1, 2, 3],  # P2
        }

        # 每个数据位影响哪些校验位
        self.data_to_parity = {
            0: [4, 5],      # D0影响P0,P1
            1: [4, 6],      # D1影响P0,P2
            2: [5, 6],      # D2影响P1,P2
            3: [4, 5, 6],  # D3影响P0,P1,P2
        }

        np.random.seed(None)

        print("=" * 60)
        print("  正确汉明码纠缠实验")
        print("=" * 60)
        print(f"数据位: {self.data_pos}")
        print(f"校验位: {self.parity_pos}")
        print(f"纠缠映射: {self.data_to_parity}")

    def encode(self, data):
        """编码: 4位数据 → 8位汉明码"""
        code = [0] * 8

        # 填入数据位
        for i, d in enumerate(data):
            code[i] = d

        # 计算校验位
        code[4] = code[0] ^ code[1] ^ code[3]  # P0
        code[5] = code[0] ^ code[2] ^ code[3]  # P1
        code[6] = code[1] ^ code[2] ^ code[3]  # P2
        code[7] = code[4] ^ code[5] ^ code[6]  # P3

        return code

    def syndrome(self, code):
        """
        计算校验子

        校验子 = 出错位的位置
        """
        s0 = code[4] ^ code[0] ^ code[1] ^ code[3]
        s1 = code[5] ^ code[0] ^ code[2] ^ code[3]
        s2 = code[6] ^ code[1] ^ code[2] ^ code[3]
        s3 = code[7] ^ code[4] ^ code[5] ^ code[6]

        syndrome = (s3 << 3) | (s2 << 2) | (s1 << 1) | s0

        return syndrome

    def inject_error(self, code):
        """注入一位错误"""
        code = code.copy()
        error_pos = np.random.randint(0, 8)
        code[error_pos] ^= 1
        return code, error_pos

    def entanglement_flip(self, code, error_pos):
        """纠缠翻转"""
        new_code = code.copy()
        entangled = []

        # 错误位触发纠缠翻转
        if error_pos in self.data_to_parity:
            entangled = self.data_to_parity[error_pos]
        elif error_pos in self.parity_to_data:
            entangled = self.parity_to_data[error_pos]

        # 翻转纠缠位
        for pos in entangled:
            new_code[pos] ^= 1

        return new_code, entangled

    def run_single(self):
        """单次试验"""
        # 随机4位数据
        data = [np.random.randint(0, 2) for _ in range(4)]

        # 编码
        original = self.encode(data)

        # 注入错误
        with_error, error_pos = self.inject_error(original)

        # 计算校验子
        syndrome = self.syndrome(with_error)

        # 纠缠翻转
        if syndrome > 0:
            final, entangled = self.entanglement_flip(with_error, syndrome)
        else:
            final = with_error.copy()
            entangled = []
            syndrome = error_pos

        return {
            'data': data,
            'original': original,
            'with_error': with_error,
            'error_pos': error_pos,
            'syndrome': syndrome,
            'entangled': entangled,
            'final': final,
            'correct': syndrome == error_pos
        }

    def run(self, n=100):
        """运行n次实验"""
        print(f"\n运行 {n} 次实验...")

        results = []
        n_correct = 0
        n_entangled = 0

        for i in range(n):
            r = self.run_single()
            results.append(r)

            if r['correct']:
                n_correct += 1
            if r['entangled']:
                n_entangled += 1

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n}")

        return results, n_correct, n_entangled

    def analyze(self, results, n_correct, n_entangled):
        """分析"""
        print(f"\n{'='*60}")
        print("  分析")
        print(f"{'='*60}")

        total = len(results)

        print(f"\n基本统计:")
        print(f"  总实验: {total}")
        print(f"  检测成功: {n_correct}/{total} = {n_correct/total*100:.1f}%")
        print(f"  纠缠翻转: {n_entangled}/{total} = {n_entangled/total*100:.1f}%")

        # 各位置纠缠统计
        ent_counts = {i: 0 for i in range(8)}
        for r in results:
            for pos in r['entangled']:
                ent_counts[pos] += 1

        print(f"\n各位置纠缠翻转次数:")
        for pos, count in sorted(ent_counts.items()):
            if count > 0:
                print(f"  位置{pos}: {count}次")

        # 最终态
        back = sum(1 for r in results if r['final'] == r['original'])
        new = total - back

        print(f"\n最终态:")
        print(f"  回到正确: {back}/{total}")
        print(f"  进入新稳态: {new}/{total}")

        return {
            'total': total,
            'correct_rate': n_correct / total * 100,
            'entangled_rate': n_entangled / total * 100,
            'back': back,
            'new': new
        }

    def show_examples(self, results, n=6):
        """展示例子"""
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  数据:  {r['data']}")
            print(f"  原始:  {r['original']}")
            print(f"  错误:  {r['with_error']} (位{r['error_pos']})")
            print(f"  校验子: {r['syndrome']}")
            if r['entangled']:
                print(f"  纠缠:  位{r['entangled']}")
            print(f"  最终:  {r['final']}")
            status = "✓正确" if r['final'] == r['original'] else "新稳态"
            print(f"  结果:  {status}")


def main():
    exp = CorrectHammingEntanglement()

    results, n_correct, n_entangled = exp.run(n=100)

    exp.show_examples(results, n=6)

    analysis = exp.analyze(results, n_correct, n_entangled)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"检测成功率: {analysis['correct_rate']:.1f}%")
    print(f"纠缠翻转率: {analysis['entangled_rate']:.1f}%")
    print(f"进入新稳态: {analysis['new']}/{analysis['total']}")

    return results, analysis


if __name__ == "__main__":
    main()