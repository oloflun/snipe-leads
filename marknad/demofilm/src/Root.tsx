import { Composition } from "remotion";
import { Film, filmDuration, type Item } from "./Film";
import film from "./data/film.json";

// data/film.json comes from rec/record-leads.mjs: the steps, their click targets and the title cards.
const FILM = film as Item[];

export const RemotionRoot: React.FC = () => (
  <Composition id="Film" component={Film} defaultProps={{ items: FILM }} durationInFrames={filmDuration(FILM)} fps={30} width={1920} height={1080} />
);
