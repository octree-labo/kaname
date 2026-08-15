import { DocumentEditPage } from "@/components/document/DocumentEditPage";
import { salesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentEditPage config={salesModule} />;
}
