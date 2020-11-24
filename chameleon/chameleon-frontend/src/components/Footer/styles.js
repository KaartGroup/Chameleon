import styled from "styled-components";

export const MainFooter = styled.div`
  font-family: "Hind Guntur", sans-serif;
  width: 100vw;
  color: #666;
  line-height: 1.7em;
  font-weight: 500;
  box-sizing: border-box;
  margin: 0;
  outline: 0;
  vertical-align: baseline;
  background: transparent;
  border: 0 solid #333;
  background-size: cover;
  position: relative;
  background-color: #fff;
  padding: 54px 0;
  border-top-width: 3px;
  border-top-color: #6a6c7c;
  padding-top: 0px;
  padding-bottom: 0px;
`;

export const Row = styled.div`
  max-width: 90%;
  margin-right: 0px !important;
  margin: auto;
  position: relative;
  padding: 27px 0;
  display: flex;
`;

export const Column = styled.div`
  text-align: left;
  font-size: 100%;
  margin-right: 6%;
  width: 20.875%;
`;

export const Header = styled.header`
  margin-bottom: 8px;
  text-transform: uppercase;
  color: #6a6c7c !important;
  text-align: left;
  font-size: 16px;
  font-weight: 700;
  background: transparent;
  padding-bottom: 0;
`;

export const UI = styled.div`
  font-weight: 300;
  font-size: 15px;
  line-height: 1.4285em;
  box-sizing: inherit;
  padding-left: 0;
  list-style: none;
`;

export const SmallRow = styled.div`
  border: 0;
  font-size: 100%;
  margin: auto;
  position: relative;
  padding: 10px 0;
  display: flex;
  background-color: #eaeaea !important;
`;

export const SmallColumn = styled.div`
  background: transparent;
  float: left;
  position: relative;
  min-height: 1px;
  mix-blend-mode: unset !important;
  margin-right: 5.5%;
  width: 47.25%;
`;

export const List = styled.div`
  display: list-item;
  text-align: -webkit-match-parent;
  margin-bottom: 2px !important;
  margin: auto;
`;

export const Link = styled.a`
  color: grey;
  &:hover {
    color: #f4753c;
  }
`;

export const Copyright = styled.div`
  text-align: center;
  font-weight: 300;
  color: #6a6c7c !important;
  line-height: 1.8em;
  font-size: 100%;
  background: transparent;
`;

export const Social = styled.div`
  text-align: center;
  font-weight: 300;
  color: #6a6c7c !important;
  font-size: 100%;
  background: transparent;
  line-height: 1.8em;
  padding-bottom: 0;
`;

export const SocialLink = styled.a`
  color: grey !important;
  filter: grayscale(20%) !important;
`;

export const SocialImage = styled.img`
  filter: grayscale(20%) !important;
  margin-right: 22px;
`;
