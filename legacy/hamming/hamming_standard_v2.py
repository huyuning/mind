#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码纠缠实验
========================================================

标准汉明码结构：
- 位置:     0  1  2  3  4  5  6
-           D0 D1 D2 D3 P0 P1 P2
- 校验位位置: 2^0=1, 2^1=2, 2^2=4 (即位置4,5,6)

校验方程：
- P0(位置4) = D0 ⊕ D1 ⊕ D2
- P1(位置5) = D0 ⊕ D2 ⊕ D3
- P2(位置6) = D1 ⊕ D2 ⊕ D3

纠缠映射（数据位影响校验位）：
- D0 → P0,P1
- D1 → P0,P2
- D2 → P0,P1,P2
- D3 → P1,P2
"""

import numpy as np
from datetime import datetime

class StandardHamming:
    def __init__(self):
        self.data_pos = [0, 1, 2, 3]
        self.parity_pos = [4, 5, 6]

        # 纠缠映射：数据位 → 校验位
        self.entanglement = {
            0: [4, 5],
            1: [4, 6],
            2: [4, 5, 6],
            3: [5, 6],
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码纠缠实验")
        print("=" * 60)
        print(f"数据位: {self.data_pos}")
        print(f"校验位: {self.parity_pos}")
        print(f"纠缠映射: {self.entanglement}")

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
        """计算校验子，确定错误位置"""
        s0 = code[4] ^ code[0] ^ code[1] ^ code[2]
        s1 = code[5] ^ code[0] ^ code[2] ^ code[3]
        s2 = code[6] ^ code[1] ^ code[2] ^ code[3]
        syndrome = (s2 << 2) | (s1 << 1) | s0
        return syndrome

    def inject_error(self, code):
        """注入一位错误"""
        err_code = code.copy()
        pos = np.random.randint(0, 7)
        err_code[pos] ^= 1
        return err_code, pos

    def resonance_flip(self, code, error_pos):
        """共振翻转 - 错误位触发纠缠位翻转"""
        new_code = code.copy()
        entangled = self.entanglement.get(error_pos, [])

        for pos in entangled:
            new_code[pos] ^= 1

        return new_code, entangled

    def run_trial(self):
        """单次试验"""
        data = [np.random.randint(0, 2) for _ in range(4)]
        original = self.encode(data)

        with_error, error_pos = self.inject_error(original)

        flipped, entangled = self.resonance_flip(with_error, error_pos)

        syndrome = self.syndrome(flipped)

        return {
            'data': data,
            'original': original,
            'error_pos': error_pos,
            'with_error': with_error,
            'flipped': flipped,
            'entangled': entangled,
            'syndrome': syndrome,
            'back_to_correct': flipped == original,
        }

    def run(self, n=100):
        """运行n次试验"""
        print(f"\n运行 {n} 次试验...")

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

        print(f"\n各位置错误统计:")
        pos_stats = {i: {'total': 0, 'back': 0} for i in range(7)}
        for r in results:
            ep = r['error_pos']
            pos_stats[ep]['total'] += 1
            if r['back_to_correct']:
                pos_stats[ep]['back'] += 1

        for pos in range(7):
            stats = pos_stats[pos]
            if stats['total'] > 0:
                print(f"  位置{pos}: {stats['total']}次错误, {stats['back']}次回到正确")

        return {
            'total': total,
            'back_rate': n_back / total * 100,
            'new_state_rate': n_new_state / total * 100,
        }

    def show_examples(self, results, n=7):
        """展示各位置例子"""
        print(f"\n{'='*60}")
        print("  各位置典型例子")
        print(f"{'='*60}")

        shown = set()
        for r in results:
            if r['error_pos'] not in shown:
                shown.add(r['error_pos'])
                print(f"\n错误位置 {r['error_pos']}:")
                print(f"  数据:   {r['data']}")
                print(f"  原始:   {r['original']}")
                print(f"  错误:   {r['with_error']}")
                print(f"  纠缠:   {r['entangled']}")
                print(f"  翻转:   {r['flipped']}")
                print(f"  校验子: {r['syndrome']}")
                print(f"  结果:   {'回到正确' if r['back_to_correct'] else '新稳态'}")
            if len(shown) >= n:
                break


def main():
    exp = StandardHamming()

    results, n_back, n_new_state = exp.run(n=100)

    exp.show_examples(results, n=7)

    analysis = exp.analyze(results, n_back, n_new_state)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"回到正确状态: {analysis['back_rate']:.1f}%")
    print(f"进入新稳态: {analysis['new_state_rate']:.1f}%")

    if analysis['new_state_rate'] > 80:
        print("\n✓ 验证：纠缠翻转导致系统进入新稳态")


if __name__ == "__main__":
    main()