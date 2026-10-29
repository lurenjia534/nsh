import { mount, Text, View } from "nsh";
import { TextView } from "nsh/base";

export function Sample(props: {
  label: string;
  fontSize?: number;
  lineHeight?: number;
  linkOffset?: number;
  rootOffset?: number;
}) {
  return (
    <View style={{ flex: 1, padding: 20, paddingTop: 64, gap: 16, backgroundColor: "#f4f6fa" }}>
      <Text style={{ fontSize: 22, lineHeight: 28, fontWeight: "700", color: "#0f172a" }}>TextView link underline</Text>
      <Text style={{ fontSize: 12, lineHeight: 18, color: "#64748b" }}>Issue #447 · platform system font</Text>
      <View style={{ padding: 16, gap: 10, borderWidth: 1, borderColor: "#d9dee7", borderRadius: 8, backgroundColor: "#ffffff" }}>
        <Text style={{ fontSize: 12, lineHeight: 18, fontWeight: "600", color: "#475569" }}>{props.label}</Text>
        <TextView
          testID="sample-document"
          markdown={"See [Native Shell](https://github.com/longbridge/nsh) for details.  \nRead [another link](https://example.com).  \n[Final-line link](https://example.com/final)"}
          styles={{
            root: {
              ...(props.fontSize === undefined ? {} : { fontSize: props.fontSize }),
              ...(props.lineHeight === undefined ? {} : { lineHeight: props.lineHeight }),
              ...(props.rootOffset === undefined ? {} : { textUnderlineOffset: props.rootOffset }),
            },
            ...(props.linkOffset === undefined ? {} : { link: { textUnderlineOffset: props.linkOffset } }),
          }}
        />
      </View>
      <Text style={{ fontSize: 12, lineHeight: 18, color: "#64748b" }}>Compare the final line's underline.</Text>
    </View>
  );
}
