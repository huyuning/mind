#!/usr/bin/env python3
"""
========================================================
汉明码纠缠共振实验 v2
========================================================

实验流程：
1. 随机生成4位数据，编码成正确汉明码
2. 随机注入一位错误
3. 用固定频率扫描（共振），检测翻转
4. 观察：是回到正确状态，还是进入新稳态

纠缠理论：
- 错误位触发与之纠缠的位同步翻转
- 系统进入新稳态而非纠正错误
"""

import numpy as np
from datetime import datetime

class HammingResonanceExperiment:
    def __init__(self):
        self.data_bits = [0, 1, 2, 3]
        self.parity_bits = [4, 5, 6, 7]

        # 数据位影响的校验位（纠缠映射）
        self.entanglement = {
            0: [4, 5],
            1: [4, 6],
            2: [5, 6],
            3: [4, 5, 6],
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  汉明码纠缠共振实验 v2")
        print("=" * 60)
        print(f"数据位: {self.data_bits}")
        print(f"校验位: {self.parity_bits}")
        print(f"纠缠映射: {self.entanglement}")
        print()

    def encode(self, data):
        """4位数据编码为8位汉明码"""
        code = [0] * 8
        for i, d in enumerate(data):
            code[i] = d
        code[4] = code[0] ^ code[1] ^ code[3]
        code[5] = code[0] ^ code[2] ^ code[3]
        code[6] = code[1] ^ code[2] ^ code[3]
        code[7] = code[4] ^ code[5] ^ code[6]
        return code

    def inject_error(self, code):
        """注入一位错误"""
        err_code = code.copy()
        pos = np.random.randint(0, 8)
        err_code[pos] ^= 1
        return err_code, pos

    def resonance_scan(self, code, error_pos):
        """
        固定频率扫描（共振）
        - 模拟固定频率激发
        - 错误位与纠缠位同步翻转
        - 返回翻转后的状态和纠缠位列表
        """
        new_code = code.copy()
        entangled = []

        if error_pos in self.entanglement:
            entangled = self.entanglement[error_pos]
            for pos in entangled:
                new_code[pos] ^= 1
        elif error_pos in [4, 5, 6]:
            for d, ps in self.entanglement.items():
                if error_pos in ps:
                    entangled.append(d)
            for pos in entangled:
                new_code[pos] ^= 1

        return new_code, entangled

    def run_trial(self):
        """单次试验"""
        data = [np.random.randint(0, 2) for _ in range(4)]
        original = self.encode(data)
        with_error, error_pos = self.inject_error(original)

        flipped, entangled = self.resonance_scan(with_error, error_pos)

        return {
            'data': data,
            'original': original,
            'error_pos': error_pos,
            'with_error': with_error,
            'flipped': flipped,
            'entangled': entangled,
            'back_to_correct': flipped == original,
        }

    def run(self, n=100):
        """运行n次试验"""
        print(f"运行 {n} 次试验...")

        results = []
        n_back = 0
        n_new_state = 0

        for i in range(n):
            r = self.run_trial()
            results.append(r)

            if r['back_to_correct']:
                n_back += 1
            else:
                n_new_state += 1

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n}")

        return results, n_back, n_new_state

    def analyze(self, results, n_back, n_new_state):
        """分析结果"""
        total = len(results)

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")

        print(f"\n基本统计:")
        print(f"  总实验: {total}")
        print(f"  回到正确状态: {n_back}/{total} = {n_back/total*100:.1f}%")
        print(f"  进入新稳态: {n_new_state}/{total} = {n_new_state/total*100:.1f}%")

        ent_counts = {i: 0 for i in range(8)}
        for r in results:
            for pos in r['entangled']:
                ent_counts[pos] += 1

        print(f"\n各位置纠缠翻转次数:")
        for pos, count in sorted(ent_counts.items()):
            if count > 0:
                print(f"  位置{pos}: {count}次 ({count/total*100:.1f}%)")

        return {
            'total': total,
            'back_rate': n_back / total * 100,
            'new_state_rate': n_new_state / total * 100,
        }

    def show_examples(self, results, n=6):
        """展示典型例子"""
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  原始数据: {r['data']}")
            print(f"  原始码:   {r['original']}")
            print(f"  错误位:   {r['error_pos']}")
            print(f"  错误码:   {r['with_error']}")
            if r['entangled']:
                print(f"  纠缠位:   {r['entangled']}")
            print(f"  翻转后:   {r['flipped']}")
            status = "回到正确" if r['back_to_correct'] else "新稳态"
            print(f"  结果:     {status}")


def main():
    exp = HammingResonanceExperiment()

    results, n_back, n_new_state = exp.run(n=100)

    exp.show_examples(results, n=6)

    analysis = exp.analyze(results, n_back, n_new_state)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"回到正确状态: {analysis['back_rate']:.1f}%")
    print(f"进入新稳态: {analysis['new_state_rate']:.1f}%")

    if analysis['new_state_rate'] > 80:
        print("\n✓ 验证假设：纠缠翻转导致系统进入新稳态，而非纠正错误")
    elif analysis['back_rate'] > 80:
        print("\n✓ 验证假设：系统回到正确状态（错误被纠正）")
    else:
        print("\n? 两种情况都有，需要更多数据")


if __name__ == "__main__":
    main()