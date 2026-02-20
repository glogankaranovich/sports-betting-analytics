"""
Calculate efficiency metrics for NFL players
"""
from typing import Dict

class NFLEfficiencyCalculator:
    
    @staticmethod
    def calculate_qb_efficiency(stats: Dict) -> float:
        """Calculate QB efficiency rating (passer rating)"""
        try:
            completions = float(stats.get('completions', 0))
            attempts = float(stats.get('passingAttempts', 0))
            yards = float(stats.get('passingYards', 0))
            tds = float(stats.get('passingTouchdowns', 0))
            ints = float(stats.get('interceptions', 0))
            
            if attempts == 0:
                return 0.0
            
            # NFL Passer Rating formula
            comp_pct = ((completions / attempts) - 0.3) * 5
            yards_per_att = ((yards / attempts) - 3) * 0.25
            td_pct = (tds / attempts) * 20
            int_pct = 2.375 - ((ints / attempts) * 25)
            
            # Clamp each component between 0 and 2.375
            comp_pct = max(0, min(comp_pct, 2.375))
            yards_per_att = max(0, min(yards_per_att, 2.375))
            td_pct = max(0, min(td_pct, 2.375))
            int_pct = max(0, min(int_pct, 2.375))
            
            rating = ((comp_pct + yards_per_att + td_pct + int_pct) / 6) * 100
            return round(rating, 2)
        except:
            return 0.0
    
    @staticmethod
    def calculate_rb_efficiency(stats: Dict) -> float:
        """Calculate RB efficiency (yards per carry + receiving)"""
        try:
            rush_yards = float(stats.get('rushingYards', 0))
            rush_att = float(stats.get('rushingAttempts', 0))
            rec_yards = float(stats.get('receivingYards', 0))
            receptions = float(stats.get('receptions', 0))
            tds = float(stats.get('rushingTouchdowns', 0)) + float(stats.get('receivingTouchdowns', 0))
            
            # Yards per touch + TD bonus
            total_touches = rush_att + receptions
            if total_touches == 0:
                return 0.0
            
            total_yards = rush_yards + rec_yards
            yards_per_touch = total_yards / total_touches
            td_bonus = tds * 2
            
            efficiency = yards_per_touch + td_bonus
            return round(efficiency, 2)
        except:
            return 0.0
    
    @staticmethod
    def calculate_wr_efficiency(stats: Dict) -> float:
        """Calculate WR efficiency (yards per reception + catch rate)"""
        try:
            receptions = float(stats.get('receptions', 0))
            targets = float(stats.get('receivingTargets', 0))
            yards = float(stats.get('receivingYards', 0))
            tds = float(stats.get('receivingTouchdowns', 0))
            
            if targets == 0:
                return 0.0
            
            # Catch rate + yards per target + TD bonus
            catch_rate = (receptions / targets) * 10
            yards_per_target = yards / targets
            td_bonus = tds * 2
            
            efficiency = catch_rate + yards_per_target + td_bonus
            return round(efficiency, 2)
        except:
            return 0.0
    
    @staticmethod
    def calculate_player_efficiency(stats: Dict, position: str = None) -> float:
        """Calculate efficiency based on player position"""
        # Try to detect position from stats
        if position is None:
            if stats.get('passingAttempts', 0) > 0:
                position = 'QB'
            elif stats.get('rushingAttempts', 0) > stats.get('receptions', 0):
                position = 'RB'
            else:
                position = 'WR'
        
        if position == 'QB':
            return NFLEfficiencyCalculator.calculate_qb_efficiency(stats)
        elif position == 'RB':
            return NFLEfficiencyCalculator.calculate_rb_efficiency(stats)
        else:
            return NFLEfficiencyCalculator.calculate_wr_efficiency(stats)
