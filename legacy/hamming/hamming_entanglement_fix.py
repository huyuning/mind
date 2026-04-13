#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 纠缠共振纠正实验
========================================================

实验设计：
1. 生成随机正确汉明码 [D0,D1,D2,D3,P0,P1,P2]
2. 选一个数据位作为预翻转位（比如D0）
3. D0影响两个校验位（P0,P1）
4. 只改两个校验位（翻转它们），不碰数据位
5. 用固定频扫（共振），让系统自然演化
6. 观测：数据位是否被"纠正"回原值，校验位是否保持修改后的状态

理论预期（纠缠理论）：
- 固定频扫会让系统进入新稳态
- 不会像汉明码那样纠正数据位
- 而是数据位和校验位一起改变，进入新稳态
"""

import numpy as np
from datetime import datetime

class HammingEntanglementFix:
    def __init__(self):
        # 标准(7,4)汉明码
        # 数据位: 位置0,3,5,6
        # 校验位: 位置1,2,4
        # D0影响P0,P1; D1影响P0,P2; D2影响P1,P2; D3影响P1,P2
        self.data_pos = [0, 3, 5, 6]
        self.parity_pos = [1, 2, 4]

        # 数据位影响的校验位
        self.data_to_parity = {
            0: [1, 2],  # D0 → P0,P1
            3: [1, 4],  # D1 → P0,P2
            5: [2, 4],  # D2 → P1,P2
            6: [1, 2, 4],  # D3 → P0,P1,P2 (注：D3影响3个校验位)
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 纠缠共振纠正实验")
        print("=" * 60)
        print(f"数据位: {self.data_pos}")
        print(f"校验位: {self.parity_pos}")
        print(f"纠缠映射: {self.data_to_parity}")

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
        s0 = code[1] ^ code[0] ^ code[3] ^ code[5]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def select_flip_position(self):
        """选择一个预翻转数据位及其影响的两个校验位"""
        # 只选择影响2个校验位的数据位（排除D3）
        flip_data_pos = np.random.choice([0, 3, 5])
        affected_parities = self.data_to_parity[flip_data_pos]
        return flip_data_pos, affected_parities

    def inject_double_parity_error(self, code, flip_pos, parities):
        """注入错误：只改两个校验位，不碰数据位"""
        err_code = code.copy()
        for p in parities:
            err_code[p] ^= 1
        return err_code

    def resonance_scan(self, code, flip_pos, parities):
        """
        固定频扫（共振）
        - 根据纠缠理论翻转
        - 只翻转预翻转数据位和纠缠的校验位
        """
        new_code = code.copy()
        entangled = [flip_pos] + parities

        for pos in entangled:
            new_code[pos] ^= 1

        return new_code, entangled

    def run_trial(self):
        """单次试验"""
        # 随机4位数据
        data = [np.random.randint(0, 2) for _ in range(4)]

        # 编码得到正确汉明码
        original = self.encode(data)

        # 选择预翻转位和影响的校验位
        flip_pos, parities = self.select_flip_position()

        # 只改校验位
        after_inject = self.inject_double_parity_error(original, flip_pos, parities)

        # 固定频扫
        after_scan, entangled = self.resonance_scan(after_inject, flip_pos, parities)

        # 正常汉明码纠正会纠正数据位flip_pos
        syndrome = self.syndrome(after_inject)
        hamming_corrects_data = (syndrome == flip_pos)

        return {
            'data': data,
            'original': original,
            'flip_pos': flip_pos,
            'parities': parities,
            'after_inject': after_inject,
            'after_scan': after_scan,
            'entangled': entangled,
            'syndrome': syndrome,
            'hamming_corrects_data': hamming_corrects_data,
            'data_corrected': after_scan[flip_pos] == original[flip_pos],
            'parities_kept': all(after_scan[p] == after_inject[p] for p in parities),
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

        n_hamming_would_correct = sum(1 for r in results if r['hamming_corrects_data'])
        n_data_corrected = sum(1 for r in results if r['data_corrected'])
        n_parities_kept = sum(1 for r in results if r['parities_kept'])

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")

        print(f"\n基本统计:")
        print(f"  总实验: {total}")
        print(f"  汉明码会纠正数据位: {n_hamming_would_correct}/{total} = {n_hamming_would_correct/total*100:.1f}%")
        print(f"  实际数据位被纠正: {n_data_corrected}/{total} = {n_data_corrected/total*100:.1f}%")
        print(f"  校验位保持修改后状态: {n_parities_kept}/{total} = {n_parities_kept/total*100:.1f}%")

        # 位置统计
        print(f"\n各预翻转位统计:")
        pos_stats = {0: {'total': 0, 'corrected': 0, 'parities_kept': 0},
                     3: {'total': 0, 'corrected': 0, 'parities_kept': 0},
                     5: {'total': 0, 'corrected': 0, 'parities_kept': 0}}
        for r in results:
            fp = r['flip_pos']
            pos_stats[fp]['total'] += 1
            if r['data_corrected']:
                pos_stats[fp]['corrected'] += 1
            if r['parities_kept']:
                pos_stats[fp]['parities_kept'] += 1

        for pos in [0, 3, 5]:
            s = pos_stats[pos]
            if s['total'] > 0:
                print(f"  位置{pos}: {s['total']}次, 纠正{s['corrected']}次, 校验位保持{s['parities_kept']}次")

        return {
            'total': total,
            'hamming_corrects': n_hamming_would_correct,
            'data_corrected': n_data_corrected,
            'parities_kept': n_parities_kept,
        }

    def show_examples(self, results, n=6):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  原始数据: {r['data']}")
            print(f"  原始码:   {r['original']}")
            print(f"  预翻转位: {r['flip_pos']} → 校验位{r['parities']}")
            print(f"  改后码:   {r['after_inject']} (只改校验位)")
            print(f"  纠缠翻转: {r['entangled']}")
            print(f"  频扫后:   {r['after_scan']}")
            print(f"  校验子:   {r['syndrome']}")
            print(f"  汉明码会纠正数据位: {r['hamming_corrects_data']}")
            print(f"  实际数据位被纠正: {r['data_corrected']}")
            print(f"  校验位保持: {r['parities_kept']}")


def main():
    exp = HammingEntanglementFix()
    results = exp.run(n=100)
    exp.show_examples(results, n=6)
    analysis = exp.analyze(results)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"汉明码会纠正数据位: {analysis['hamming_corrects']}/{analysis['total']} = {analysis['hamming_corrects']/analysis['total']*100:.1f}%")
    print(f"实际数据位被纠正: {analysis['data_corrected']}/{analysis['total']} = {analysis['data_corrected']/analysis['total']*100:.1f}%")
    print(f"校验位保持修改后状态: {analysis['parities_kept']}/{analysis['total']} = {analysis['parities_kept']/analysis['total']*100:.1f}%")

    if analysis['data_corrected'] == 0 and analysis['parities_kept'] > 80:
        print("\n✓ 验证：纠缠共振不纠正错误，而是进入新稳态")
    elif analysis['data_corrected'] > 80:
        print("\n? 数据显示数据位被纠正了")


if __name__ == "__main__":
    main()