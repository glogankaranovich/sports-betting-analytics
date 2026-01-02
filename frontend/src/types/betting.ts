export interface Outcome {
  name: string;
  price: number;
  point?: number;
}

export interface Market {
  outcomes: Outcome[];
}

export interface Game {
  game_id: string;
  sport: string;
  commence_time: string;
  home_team: string;
  away_team: string;
  updated_at: string;
  odds: {
    [bookmaker: string]: {
      [market: string]: Market;
    };
  };
}

export interface PlayerProp {
  pk: string;
  sk: string;
  sport: string;
  event_id: string;
  bookmaker: string;
  market_key: string;
  player_name: string;
  outcome: string;
  point: number;
  price: number;
  updated_at: string;
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

export interface PlayerPropsResponse {
  props: PlayerProp[];
  count: number;
  filters: {
    sport?: string;
    player?: string;
    prop_type?: string;
  };
}
