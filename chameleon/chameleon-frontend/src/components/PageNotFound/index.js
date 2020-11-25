import React from "react";
import { NotFoundWrapper, TestText } from "./styles";


export const PageNotFound = () => {

  return (
    <>
      <NotFoundWrapper>
        <TestText>
            <p style={{ textAlign: "center" }}>
              <br></br>
              404 - Page Not Found
              <br></br>
              <br></br>
              <br></br>
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus
              mattis eget elit ac bibendum. In nec elit vel erat convallis
              lacinia sed eu metus. Nullam viverra ante nisi, non facilisis
              erat egestas in. Maecenas quam nulla, rhoncus in mauris ac,
              ornare tincidunt tellus. Praesent et commodo elit. Pellentesque
              habitant morbi tristique senectus et netus et malesuada fames ac
              turpis egestas.
              <br></br>
              <br></br>
              Fusce volutpat massa eros, non dapibus nisi
              auctor vitae. Nunc aliquet ipsum sed felis tempus suscipit.
              Fusce vitae nibh id arcu sagittis malesuada venenatis ac lacus.
              Aliquam ex odio, egestas id eros eu, facilisis sodales ipsum.
              Etiam commodo nisi sapien, sit amet semper tortor venenatis
              vitae. Fusce eget metus quam. Nulla sit amet blandit nisl, sed
              facilisis velit. Aenean faucibus lacinia neque nec porta. Duis
              tempor, metus id placerat porttitor, neque ipsum tempor dui,
              quis elementum enim metus eget felis.
              <br></br>
              <br></br>
              <br></br>
              <button onClick={() => (window.location = "/")}>Go Back</button>
              <br></br>
              <br></br>
              <br></br>
            </p>
          </TestText>
      </NotFoundWrapper>
    </>
  );
};

