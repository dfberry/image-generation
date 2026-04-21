import {Composition, getInputProps} from 'remotion';
import GeneratedScene from './GeneratedScene';

const inputProps = getInputProps();

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="GeneratedScene"
        component={GeneratedScene}
        durationInFrames={inputProps?.durationInFrames ?? 150}
        fps={inputProps?.fps ?? 30}
        width={inputProps?.width ?? 1280}
        height={inputProps?.height ?? 720}
      />
    </>
  );
};
