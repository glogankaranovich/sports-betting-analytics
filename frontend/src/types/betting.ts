export interface Game {
  game_id: string;
  sport: string;
  commence_time: string;
  home_team: string;
  away_team: string;
  bookmaker: string;
  markets: {
    h2h?: {
      home: number;
      away: number;
    };
    spreads?: {
      home: number;
      away: number;
      home_point: number;
      away_point: number;
    };
    totals?: {
      over: number;
      under: number;
      point: number;
    };
  };
}

export interface Sport {
  key: string;
  title: string;
  description: string;
  active: boolean;
  has_outrights: boolean;
}

export interface Bookmaker {
  key: string;
  title: string;
}

export interface ApiResponse {
  games: Game[];
  count: number;
  sport_filter: string | null;
}
