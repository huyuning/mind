#!/usr/bin/env python3
"""
========================================================
汉明码纠缠共振实验 v3 - 完整验证
========================================================

关键验证：
1. 所有8个位置都能触发共振（都应该有纠缠）
2. 固定频率扫描后，系统进入新稳态
3. 汉明码应该能检测和定位任何位置的错误
"""

import numpy as np
from datetime import datetime

class HammingV3:
    def __init__(self):
        # 8个位置全参与纠缠
        # 数据位: 0,1,2,3
        # 校验位: 4,5,6,7
        # 每个校验位也参与纠缠（标准汉明码的校验位互相验证）

        # 完整纠缠映射 - 包括校验位之间的纠缠
        # P3(位置7)应该由P0,P1,P2校验，所以位置7会影响这些位
        self.entanglement = {
            0: [4, 5],      # D0 → P0,P1
            1: [4, 6],      # D1 → P0,P2
            2: [5, 6],      # D2 → P1,P2
            3: [4, 5, 6],  # D3 → P0,P1,P2
            # 校验位出错也应该触发纠缠
            4: [0, 1, 3, 7],  # P0 → D0,D1,D3,P3
            5: [0, 2, 3, 7],  # P1 → D0,D2,D3,P3
            6: [1, 2, 3, 7],  # P2 → D1,D2,D3,P3
            7: [4, 5, 6],     # P3 → P0,P1,P2
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  汉明码纠缠共振实验 v3")
        print("=" * 60)
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
        """固定频率扫描 - 纠缠翻转"""
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

    def run(self, n=1000):
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

            if (i + 1) % 200 == 0:
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

        # 各错误位置的统计
        print(f"\n各错误位置统计:")
        pos_stats = {i: {'total': 0, 'back': 0, 'entangled': []} for i in range(8)}
        for r in results:
            ep = r['error_pos']
            pos_stats[ep]['total'] += 1
            if r['back_to_correct']:
                pos_stats[ep]['back'] += 1
            pos_stats[ep]['entangled'].extend(r['entangled'])

        for pos in range(8):
            stats = pos_stats[pos]
            if stats['total'] > 0:
                ent_set = set(stats['entangled'])
                print(f"  位置{pos}: {stats['total']}次错误, {stats['back']}次回到正确, 纠缠位{ent_set}")

        # 各位置被翻转次数
        ent_counts = {i: 0 for i in range(8)}
        for r in results:
            for pos in r['entangled']:
                ent_counts[pos] += 1

        print(f"\n各位置被纠缠翻转次数:")
        for pos, count in sorted(ent_counts.items()):
            print(f"  位置{pos}: {count}次 ({count/total*100:.1f}%)")

        return {
            'total': total,
            'back_rate': n_back / total * 100,
            'new_state_rate': n_new_state / total * 100,
            'pos_stats': pos_stats,
        }

    def show_examples(self, results, n=8):
        """展示各位置的典型例子"""
        print(f"\n{'='*60}")
        print("  各位置典型例子")
        print(f"{'='*60}")

        shown = set()
        for r in results:
            if r['error_pos'] not in shown:
                shown.add(r['error_pos'])
                print(f"\n错误位置 {r['error_pos']}:")
                print(f"  原始: {r['original']}")
                print(f"  错误: {r['with_error']}")
                print(f"  纠缠: {r['entangled']}")
                print(f"  翻转: {r['flipped']}")
                print(f"  结果: {'回到正确' if r['back_to_correct'] else '新稳态'}")
            if len(shown) >= n:
                break


def main():
    exp = HammingV3()

    results, n_back, n_new_state = exp.run(n=1000)

    exp.show_examples(results, n=8)

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
        print("\n? 两种情况都有")


if __name__ == "__main__":
    main()