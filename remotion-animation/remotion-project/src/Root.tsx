import {Composition} from 'remotion';
import GeneratedScene from './GeneratedScene';

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="GeneratedScene"
        component={GeneratedScene}
        durationInFrames={150}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};
