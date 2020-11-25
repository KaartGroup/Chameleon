import React, { useState } from "react";
import ReactGridLayout, { WidthProvider } from "react-grid-layout";
import Button from "@material-ui/core/Button";

import { FileDetails } from "../FileDetails";
import { How } from "../How";
import { Heading, Wrapper } from "./styles";
import { SubmitForm } from "../Submit";


const GridLayout = WidthProvider(ReactGridLayout);

export const BYOD = () => {
  const [name, setName] = useState("Old File")
  const [layouts, setLayouts] = useState({});

  const onLayoutChange = (layouts) => {
    setLayouts(layouts);
  };

  const getViewHeight = () => {
    return window.innerHeight;
  };


  return (
    <>
    <GridLayout
        measureBeforeMount={true}
        className="layout"
        cols={6}
        containerPadding={[10, 10]}
        rowHeight={getViewHeight() / 2}
        margin={[10, 10]}
        layouts={layouts}
        onLayoutChange={(layout) => onLayoutChange(layout)}
      >
        <div
        className="byod"
        key="1"
        data-grid={{
          x: 0,
          y: 0,
          w: 3,
          h: 1,
          i: "byod_grid",
          static: true,
          }}
        >
          <Wrapper><Heading><abbr style={{ textDecoration: "none" }} title="Bring Your Own Data">BYOD</abbr></Heading></Wrapper>
            <Button
              variant="contained"
              component="label"
              >
              { name }
              <input
                  type="file"
                  hidden
                  onChange={() => { setName(name + " ✓")}}
              />
              </Button>
              <Button
              variant="contained"
              component="label"
              >
              New File
              <input
                  type="file"
                  hidden
              />
              </Button>
              <How />
        </div>
        <div
          className="what"
          key="2"
          data-grid={{
            x: 5,
            y: 0,
            w: 3,
            h: 1,
            i: "what_grid",
            static: true,
            }}
          >
            <FileDetails />
            <SubmitForm />
          </div>
      </GridLayout>
    </>
  );
};

